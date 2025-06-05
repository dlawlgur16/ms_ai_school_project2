from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
import matplotlib.pyplot as plt
from collections import Counter, defaultdict
from dotenv import load_dotenv
import gradio as gr
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
from bson import ObjectId
import requests
import os
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans, AgglomerativeClustering
import json
import webbrowser
from io import BytesIO
import base64
from openai import AzureOpenAI
from jinja2 import Template


client = MongoClient("mongodb+srv://team9:1q2w3e4r!@6th-team9-2nd-db.global.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000")
db = client["6a013"]
collection = db["chat_logs"]

azure_oai_endpoint = os.getenv("AZURE_OAI_ENDPOINT")
azure_oai_key = os.getenv("AZURE_OAI_KEY")

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

# Review stages (label and time delta for each stage)
REVIEW_STAGES = [
    ("1차 복습", timedelta(days=1)),
    ("2차 복습", timedelta(days=7)),
    ("3차 복습", timedelta(days=30))
]

# 질문 통계 함수
def get_stats(user_id):
    docs = list(collection.find({"user_id": user_id}))
    now = datetime.now(timezone.utc)
    labels, due, done = [], [], []

    for i, (label, delta) in enumerate(REVIEW_STAGES):
        d, dn = 0, 0
        for doc in docs:
            dt = datetime.fromisoformat(doc["datetime"].replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)  # ✅ 타임존-aware로 보정
            base = dt if doc.get("review_counts", 0) == 0 else datetime.fromisoformat(doc.get("review_date", dt.isoformat()).replace("Z", "+00:00"))
            if base.tzinfo is None:
                base = base.replace(tzinfo=timezone.utc)
            rc = doc.get("review_counts", 0)
            if rc <= i and base + delta < now:
                d += 1
            elif rc > i:
                dn += 1
        labels.append(label)
        due.append(d)
        done.append(dn)

    # 그리기
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar(labels, due, label="복습 필요", color="#ff6b6b")
    ax.bar(labels, done, bottom=due, label="복습 완료", color="#4caf50")
    ax.set_ylabel("질문 수")
    ax.set_title("복습 현황")
    ax.legend()
    return fig

# 전체 학습자(본인 제외) 질문 확인 함수
def load_popular_questions(user_id):
    cursor = collection.find({"user_id": {"$ne": user_id}}, {"query": 1})
    queries = [doc["query"] for doc in cursor if "query" in doc]
    counter = Counter(queries)
    sorted_questions = counter.most_common(30)
    top_list = [f"{q} - {count}회" for q, count in sorted_questions]
    return gr.update(choices=top_list), pd.DataFrame(sorted_questions, columns=["질문", "횟수"])

### 🔹 최근 질문 20개 불러오기 (라디오 버튼용)
def load_recent_questions():
    db = client["6a013"]
    collection = db["chat_logs"]

    cursor = collection.find({}, {"query": 1, "timestamp": 1}) \
        .sort("timestamp", -1).limit(20)

    labels = []
    for doc in cursor:
        query = doc.get("query")
        ts = doc.get("timestamp")
        if query:
            label = f"{query} ({ts.strftime('%Y-%m-%d %H:%M')})" if ts else query
            labels.append(label)
    print("labels:",labels)
    return gr.update(choices=labels)

def load_all_questions_summary():
    cursor = collection.find({}, {"query": 1, "summary": 1, "timestamp": 1}) \
        .sort("timestamp", -1)

    rows = []
    for doc in cursor:
        ts = doc.get("timestamp")
        query = doc.get("query", "")
        summary = doc.get("summary", "")
        time_str = ts.strftime('%Y-%m-%d %H:%M') if ts else ""
        rows.append({
            "질문": query,
            "요약": summary
        })

    df = pd.DataFrame(rows)
    print(df)
    return df

def cluster_questions(n_clusters=7):
    # MongoDB에서 질문과 벡터 로드
    docs = list(collection.find({"query_vectorized": {"$exists": True}}))
    queries, answers, vectors = [], [], []

    for doc in docs:
        vec = doc.get("query_vectorized")
        if vec and isinstance(vec, list) and all(isinstance(x, (int, float)) for x in vec) and len(vec) == 1536:
            vectors.append(vec)
            queries.append(doc["query"])
            answers.append(doc["answer"])

    if len(vectors) < n_clusters:
        return [], "❗ 클러스터 수보다 질문이 적습니다.", {}, [], []

    X = np.array(vectors)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    clusters = {i: [] for i in range(n_clusters)}
    for i, label in enumerate(labels):
        clusters[label].append((queries[i], answers[i]))

    cluster_keywords = {}
    for cid, items in clusters.items():
        texts = [q for q, _ in items]
        tfidf = TfidfVectorizer(stop_words='english')
        X = tfidf.fit_transform(texts)
        scores = X.sum(axis=0)
        words = [(word, scores[0, idx]) for word, idx in tfidf.vocabulary_.items()]
        sorted_words = sorted(words, key=lambda x: x[1], reverse=True)
        cluster_keywords[cid] = [w[0] for w in sorted_words[:3]]

    keyword_choices = [", ".join(cluster_keywords[i]) for i in range(n_clusters)]
    question_map = {", ".join(cluster_keywords[i]): clusters[i] for i in range(n_clusters)}

    return keyword_choices, "✅ 클러스터링 완료", question_map, queries, answers

def delete_question(selected_id, docs):
    try:
        obj_id = ObjectId(selected_id)
    except Exception as e:
        return gr.update(choices=[]), [], f"삭제 오류: {e}", "", "", gr.update(visible=False)
    collection.delete_one({"_id": obj_id})
    return gr.update(choices=[]), [], "", "", "", gr.update(visible=False)




def generate_cluster_name_from_keywords(keywords):
    prompt = f"다음 키워드들을 가장 잘 대표할 수 있는 하나의 간단한 한국어 키워드로 요약해줘. 가능한 한 의미 있는 명사로 작성해줘:\n키워드: {', '.join(keywords)}"
    headers = {"Content-Type": "application/json", "api-key": azure_oai_key}
    body = {
        "messages": [
            {"role": "system", "content": "당신은 클러스터 키워드들을 받아 한국어로 간결하고 의미 있는 대표 키워드를 생성하는 AI입니다. 답변에는 따옴표를 포함하지 않습니다."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5, "top_p": 0.9, "max_tokens": 50
    }
    try:
        response = requests.post(azure_oai_endpoint, headers=headers, json=body)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
    except:
        pass
    return "미정_키워드"





def get_vectorized_docs():
    collection = db["chat_logs_yj"]
    return list(collection.find({"query_vectorized": {"$exists": True, "$type": "array"}}))

def cluster_questions_kmeans(n_clusters):
    docs = get_vectorized_docs()
    if len(docs) < n_clusters:
        return [], f"❗ 질문 수({len(docs)}) < 클러스터 수({n_clusters})", {}

    queries, answers, vectors = [], [], []
    for doc in docs:
        vec = doc["query_vectorized"]
        if len(vec) == 1536:
            queries.append(doc["query"])
            answers.append(doc["answer"])
            vectors.append(vec)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(np.array(vectors))

    clusters = defaultdict(list)
    for i, label in enumerate(labels):
        clusters[label].append((queries[i], answers[i]))

    question_map = {}
    for cid, items in clusters.items():
        texts = [q for q, _ in items]
        tfidf = TfidfVectorizer(stop_words='english')
        X_tfidf = tfidf.fit_transform(texts)
        scores = X_tfidf.sum(axis=0)
        words = [(word, scores[0, idx]) for word, idx in tfidf.vocabulary_.items()]
        top_keywords = [w[0] for w in sorted(words, key=lambda x: x[1], reverse=True)[:3]]
        keyword = generate_cluster_name_from_keywords(top_keywords)
        question_map[keyword] = items
    return list(question_map.keys()), "✅ KMeans 완료", question_map

def cluster_questions_similarity(threshold):
    docs = get_vectorized_docs()
    if len(docs) < 2:
        return [], "❗ 유사도 클러스터링을 위한 질문 수 부족", {}

    queries, answers, vectors = [], [], []
    for doc in docs:
        vec = doc["query_vectorized"]
        if len(vec) == 1536:
            queries.append(doc["query"])
            answers.append(doc["answer"])
            vectors.append(vec)

    sim_matrix = cosine_similarity(vectors)
    dist_matrix = 1 - sim_matrix

    clustering = AgglomerativeClustering(metric='precomputed', linkage='complete', distance_threshold=1 - threshold, n_clusters=None)
    labels = clustering.fit_predict(dist_matrix)

    clusters = defaultdict(list)
    for i, label in enumerate(labels):
        clusters[label].append((queries[i], answers[i]))

    question_map = {}
    for cid, items in clusters.items():
        texts = [q for q, _ in items]
        tfidf = TfidfVectorizer(stop_words='english')
        X_tfidf = tfidf.fit_transform(texts)
        scores = X_tfidf.sum(axis=0)
        words = [(word, scores[0, idx]) for word, idx in tfidf.vocabulary_.items()]
        top_keywords = [w[0] for w in sorted(words, key=lambda x: x[1], reverse=True)[:3]]
        keyword = generate_cluster_name_from_keywords(top_keywords)
        question_map[keyword] = items
    return list(question_map.keys()), "✅ Similarity 완료", question_map

def generate_kmeans_similarity_statistics():
    plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지
    plt.rcParams.update({'axes.titlesize': 14, 'xtick.labelsize': 10, 'ytick.labelsize': 10})
    collection = db["chat_logs_yj"]
    logs = list(collection.find({}))

    def count_by_level(logs, category_field):
        basic_counter, adv_counter = Counter(), Counter()
        basic_time, adv_time = Counter(), Counter()

        for log in logs:
            level = log.get("level", "unknown")
            dt_str = log.get("datetime")
            try:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                hour_key = f"{dt.hour:02d}시"
            except:
                hour_key = "unknown"

            cat = log.get(category_field)
            if cat:
                if level == "basic":
                    basic_counter[str(cat)] += 1
                    basic_time[hour_key] += 1
                elif level == "advanced":
                    adv_counter[str(cat)] += 1
                    adv_time[hour_key] += 1

        return basic_counter, adv_counter, basic_time, adv_time

    kmeans_b, kmeans_a, kmeans_bt, kmeans_at = count_by_level(logs, "category_kmeans")
    sim_b, sim_a, sim_bt, sim_at = count_by_level(logs, "category_similarity")

    def plot_grouped_bar(b_counter, a_counter, title):
        labels = sorted(set(b_counter.keys()).union(a_counter.keys()))
        b_vals = [b_counter.get(k, 0) for k in labels]
        a_vals = [a_counter.get(k, 0) for k in labels]
        x = np.arange(len(labels))
        width = 0.35

        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar(x - width/2, b_vals, width, label='Basic', color='skyblue')
        ax.bar(x + width/2, a_vals, width, label='Advanced', color='orange')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30)
        ax.set_title(title)
        ax.set_ylabel("질문 수")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.5)
        return fig

    def plot_dual_line(b_time, a_time, title):
        keys = sorted(set(b_time.keys()).union(a_time.keys()), key=lambda x: int(x.replace("시", "")) if x != "unknown" else -1)
        b_vals = [b_time.get(k, 0) for k in keys]
        a_vals = [a_time.get(k, 0) for k in keys]

        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(keys, b_vals, label="Basic", marker='o', color='blue')
        ax.plot(keys, a_vals, label="Advanced", marker='s', color='red')
        ax.set_title(title)
        ax.set_ylabel("질문 수")
        ax.set_xlabel("시간대")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.5)
        return fig

    return (
        plot_grouped_bar(kmeans_b, kmeans_a, "KMeans 카테고리별 질문 수 (basic vs advanced)"),
        plot_grouped_bar(sim_b, sim_a, "Similarity 카테고리별 질문 수 (basic vs advanced)"),
        plot_dual_line(kmeans_bt, kmeans_at, "시간대별 KMeans 질문 수 (basic vs advanced)"),
        plot_dual_line(sim_bt, sim_at, "시간대별 Similarity 질문 수 (basic vs advanced)")
    )

def save_chart(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()

def generate_line_chart(basic_data, adv_data):
    df = pd.DataFrame({"시간대": sorted(set(basic_data) | set(adv_data))})
    df["Basic"] = df["시간대"].map(basic_data).fillna(0)
    df["Advanced"] = df["시간대"].map(adv_data).fillna(0)

    fig, ax = plt.subplots()
    ax.plot(df["시간대"], df["Basic"], marker='o', linewidth=2.5, label='Basic')
    ax.plot(df["시간대"], df["Advanced"], marker='o', linewidth=2.5, label='Advanced')
    ax.set_title("시간대별 질문 수 (Basic vs Advanced)")
    ax.set_xlabel("시간대")
    ax.set_ylabel("질문 수")
    ax.legend()
    plt.xticks(rotation=45)
    return save_chart(fig)

def generate_grouped_bar_chart(basic_count, adv_count, title, xlabel):
    labels = sorted(set(basic_count) | set(adv_count))
    x = range(len(labels))
    basic = [basic_count.get(l, 0) for l in labels]
    adv = [adv_count.get(l, 0) for l in labels]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar([i - 0.2 for i in x], basic, width=0.4, label="Basic", color="#4c72b0")
    ax.bar([i + 0.2 for i in x], adv, width=0.4, label="Advanced", color="#dd8452")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("질문 수")
    ax.legend()
    return save_chart(fig)

def generate_html_report():
    collection = db["chat_logs_yj"]
    logs = list(collection.find({
        "category_kmeans": {"$exists": True},
        "category_similarity": {"$exists": True},
        "level": {"$in": ["basic", "advanced"]},
        "datetime": {"$exists": True}
    }))

    kmeans_clustered, sim_clustered = defaultdict(list), defaultdict(list)
    hour_basic, hour_adv = Counter(), Counter()
    kmeans_basic, kmeans_adv = Counter(), Counter()
    sim_basic, sim_adv = Counter(), Counter()
    gpt_logs_summary = []

    for log in logs:
        query = log["query"]
        level = log["level"]
        cat_k = log["category_kmeans"]
        cat_s = log["category_similarity"]
        time = datetime.fromisoformat(log["datetime"].replace("Z", "+00:00"))
        hour = f"{time.hour:02d}:00"

        kmeans_clustered[cat_k].append(query)
        sim_clustered[cat_s].append(query)

        if level == "basic":
            hour_basic[hour] += 1
            kmeans_basic[cat_k] += 1
            sim_basic[cat_s] += 1
        else:
            hour_adv[hour] += 1
            kmeans_adv[cat_k] += 1
            sim_adv[cat_s] += 1

        gpt_logs_summary.append({
            "level": level,
            "category_kmeans": cat_k,
            "category_similarity": cat_s,
            "datetime": log["datetime"]
        })

    charts = {
        "hour": generate_line_chart(hour_basic, hour_adv),
        "kmeans": generate_grouped_bar_chart(kmeans_basic, kmeans_adv, "KMeans 카테고리별 질문 수", "카테고리"),
        "similarity": generate_grouped_bar_chart(sim_basic, sim_adv, "Similarity 카테고리별 질문 수", "카테고리")
    }

    gpt_summary = json.dumps(gpt_logs_summary[:30], ensure_ascii=False, indent=2)
    client_oai = AzureOpenAI(api_key=azure_oai_key, azure_endpoint=azure_oai_endpoint, api_version="2023-07-01-preview")
    gpt_response = client_oai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "너는 GPTutor 교수자 분석 도구의 AI야. "
                    "아래 데이터를 기반으로 HTML 보고서에 맞는 분석 인사이트를 출력해줘."
                    "각 인사이트는 <div class='insight-block'>...</div> 구조를 따르며 표나 리스트를 활용할 수 있어."
                    "마크다운 기호는 포함하지 마."
                    "level에서 basic은 기초반, advanced는 심화반을 의미해"
                )
            },
            {
                "role": "user",
                "content": (
                        "다음은 학생 질문 메타데이터입니다. level, category_kmeans, category_similarity, datetime을 포함합니다."
                        + gpt_summary)
            }
        ],
        temperature=0.4
    )

    feedback = gpt_response.choices[0].message.content.strip().replace("```html", "").replace("```", "")

    with open("template.html", encoding="utf-8") as f:
        template = Template(f.read())

    rendered_html = template.render(
        created=datetime.now().strftime("%Y-%m-%d"),
        charts=charts,
        kmeans_clustered=kmeans_clustered,
        sim_clustered=sim_clustered,
        feedback=feedback
    )

    with open("report.html", "w", encoding="utf-8") as f:
        f.write(rendered_html)

    return "✅ report.html 생성 완료! '리포트 열기'를 눌러 확인해보세요."

def open_report_in_browser():
    path = os.path.abspath("report.html")
    webbrowser.open(f"file://{path}")
    return "🌐 브라우저에서 report.html 열렸습니다."






