# Import necessary libraries
import os
import re
import requests
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient
from sklearn.metrics.pairwise import cosine_similarity

# Load environment variables (requires a `.env` file with proper keys)
from dotenv import load_dotenv
from vector.vectorize import vectorize

load_dotenv()

azure_oai_endpoint = os.getenv("AZURE_OAI_ENDPOINT")
azure_oai_key = os.getenv("AZURE_OAI_KEY")
azure_oai_deployment = os.getenv("AZURE_OAI_DEPLOYMENT")

azure_textembedding_endpoint = os.getenv("AZURE_TEXTEMBEDDING_ENDPOINT")
azure_textembedding_key = os.getenv("AZURE_TEXTEMBEDDING_KEY")

azure_search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
azure_search_key = os.getenv("AZURE_SEARCH_KEY")

azure_services_endpoint = os.getenv("AZURE_SERVICES_ENDPOINT")
azure_services_key = os.getenv("AZURE_SERVICES_KEY")

cosmos_endpoint = os.getenv("COSMOSDB_NOSQL_ENDPOINT")
cosmos_key = os.getenv("COSMOSDB_NOSQL_KEY")
mongodb_uri = os.getenv("MONGODB_URI")

client = MongoClient(mongodb_uri)
db = client["6a013"]
collection = db["chat_logs"]

mcq_cache = {}
# MongoDB 초기화
def initialize_database(db_name,collection_name):
    client = MongoClient(mongodb_uri)
    db = client[db_name]  # 데이터베이스 이름
    collection = db[collection_name]  # 카테고리 컬렉션
    return collection

# GPT 질문 답변 함수
def ask_gpt(user_id, query,max_tokens=800):
    endpoint = azure_oai_endpoint
    key = azure_oai_key
    headers = {
        "Content-Type":"application/json",
        "api-key":key
    }
    payload = {
        "messages": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "사용자 질문에 대해 200자로 알기 쉽게 답변합니다. 답변의 앞부분에는 [대분류 카테고리: 소분류 카테고리] 형식으로 인식한 질문 카테고리를 포함해 답변합니다. 카테고리는 최대한 세부적으로 넣어야합니다."
                    }
                ]
            },
            {
                "role": "user",
                "content": query
            }
        ],
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": max_tokens
    }
    response = requests.post(endpoint, headers=headers, json=payload)
    if response.status_code == 200:
        response_json = response.json()
        answer = response_json["choices"][0]["message"]["content"]
        # 채팅 로그 저장
        unix_time = response_json['created']
        KST = timezone(timedelta(hours=9))
        dt = datetime.fromtimestamp(unix_time, tz=KST)

        return answer, dt

def summery_function(answer):
    ta_credential = AzureKeyCredential(azure_services_key) #요약함수는 따로
    client = TextAnalyticsClient(endpoint=azure_services_endpoint,credential=ta_credential)
    # 응답 요청
    poller = client.begin_abstract_summary([answer], sentence_count=1, language="ko")
    summary = ""
    abstract_summary_results = poller.result()
    for result in abstract_summary_results:
        if result.kind == "AbstractiveSummarization":
            for content in result.summaries:
                summary += content.text
        elif result.is_error is True:
            print("...Is an error with code '{}' and message '{}'".format(result.error.code, result.error.message))
    return summary

# 사용자 쿼리를 평가하고 적합한 카테고리에 추가
def process_user_query(query,categories_collection):

    query_embedding = vectorize(query)

    documents = list(categories_collection.find({}))

    best_match = None
    best_score = -1

    for document in documents:
        subcategory_embedding = document["subcategoryvector"]
        similarity = cosine_similarity([query_embedding], [subcategory_embedding])[0][0]

        if similarity > best_score:
            best_score = similarity
            best_match = document

    # ✅ 유사도가 충분히 높을 때만 저장
    threshold = 0.44 # 너가 원하는 기준에 맞게 조절 가능

    if best_match and best_score >= threshold:
        categories_collection.update_one(
            {"_id": best_match["_id"]},
            {"$push": {"questions": query}}
        )
        category_name = best_match["category"]
        subcategory_name = best_match["subcategory"]
        print(f"'{query}' 질문이 '{category_name}'의 '{subcategory_name}' 하위 항목에 추가되었습니다.(유사도: {best_score:.2f})")
    else:
        category_name, subcategory_name = "기타", "기타"
        print(f"'{query}'는 적합한 카테고리를 찾지 못했습니다. (유사도: {best_score:.2f})")

    return category_name, subcategory_name

def gpt_category(user_id, query,max_tokens):
    answer, dt = ask_gpt(user_id, query, max_tokens)
    categories_collection= initialize_database("6a055","category_classified")
    logs_collection = initialize_database("6a055","chat_logs")

    category_name, subcategory_name =process_user_query(query, categories_collection)
    results = "질문이 처리되었습니다."  # 실제 응답 로직이 있다면 여기에 추가
    summary = summery_function(answer)
    print(results)

    chat_log = {
        "user_id": user_id,
        "datetime": dt.isoformat(),
        "query": query,
        "answer": answer,
        "summary": summary,
        "timestamps":"",
        "category": {
            "category_name": category_name,
            "subcategory_name": subcategory_name
        }

    }
    print(chat_log)


    return chat_log

# 답, chat_log 반환 함수
def ask_gpt_answer_only(user_id, query,max_tokens=800):
    chat_log =gpt_category(user_id, query,max_tokens)

    return chat_log

# NOTE: 함수 파라미터 추가 & 기능 변경경
# 문제 생성 함수
def create_gpt(difficulty, query, answer):
    headers = {
        "Content-Type": "application/json",
        "api-key": azure_oai_key
    }
    payload = {
        "messages": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "사용자가 보내는 질문, 답변 세트에 기반해 관련 내용을 학습할 수 있는 문제를 난이도 1, 2, 3으로 각 1개씩 총 3개 생성합니다. 문제 형식은 사지선다 객관식입니다. 다른 형식의 문제는 생성하지 않습니다. 문제의 답변은 네 가지 선택지 중 하나입니다. 선택지는 반드시 줄마다 a), b), c), d) 형식으로 시작해야 합니다. 새로 생성하는 문제는 다양하게 생성될 수 있지만 답변 형식과 구조는 <난이도: #난이도>\n문제: <문제>\n답: <답>\n해설: <해설>#로 항상 똑같해야 합니다. 난이도, 문제, 답, 그리고 해설은 항상 빈칸(\n)으로 구분하고 각 난이도의 문제는 '\n---\n' 로 구분합니다. 마지막 줄에는 답이 무엇인지 해설과 함께 설명합니다."
                    }
                ]
            },
            {
                "role": "user",
                "content": f"질문: {query}\n답변: {answer}"
            }
        ],
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 800
    }

    response = requests.post(azure_oai_endpoint, headers=headers, json=payload)
    if response.status_code == 200:
        content = response.json()["choices"][0]["message"]["content"]
        """
        mcq_cache["full"] = content

        mcq_cache["correct"] = ""
        for line in content.split("\n"):
            if line.startswith("답:"):
                clean = line.replace("답:", "").strip().lower()
                if clean:
                    mcq_cache["correct"] = clean[0]
                break

        lines = content.split("\n")
        question_only = []
        for line in lines:
            if line.startswith("답:") or line.startswith("해설:") or line.startswith("답은"):
                break
            question_only.append(line)
        formatted = "\n".join(question_only)
        formatted = re.sub(r"(?<!\n)([a-d]\))", r"\n\1", formatted)

        if "a)" not in formatted or "b)" not in formatted:
            return "⚠️ 선택지가 포함되지 않은 문제입니다. 다시 생성해 주세요."

        return formatted.strip()
        """

        # NOTE:
        mcq_cache["raw"] = content
        mcq_cache["levels"] = {0 : {}, 1: {}, 2: {}}
        difficulty_map = {"난이도 1": 0, "난이도 2": 1, "난이도 3": 2}
        difficulty = difficulty_map.get(difficulty, -1)

        mcq_list = [item.strip() for item in content.split('---') if item.strip()]

        if len(mcq_list) == 3:
            for level, quiz in enumerate(mcq_list):
                question_lines = []
                for line in quiz.split("\n"):
                    if line.startswith("답:"):
                        ans = line.replace("답:", "").strip().lower()
                        if ans:
                            mcq_cache["levels"][level]["answer"] = ans[0]
                        continue

                    elif line.startswith("해설:"):
                        txt = line.replace("해설:", "").strip().lower()
                        if txt:
                            mcq_cache["levels"][level]["context"] = txt
                        continue
                    else:
                        question_lines.append(line)
                question = "\n".join(question_lines)
                mcq_cache["levels"][level]["question"] = question



            #return mcq_list[0],  mcq_cache["levels"][0]["answer"], mcq_list[1],  mcq_cache["levels"][1]["answer"], mcq_list[2],  mcq_cache["levels"][2]["answer"]
            #return mcq_cache["levels"][0]["question"], mcq_cache["levels"][0]["answer"], mcq_cache["levels"][1]["question"], mcq_cache["levels"][1]["answer"], mcq_cache["levels"][2]["question"], mcq_cache["levels"][2]["answer"]
            #return mcq_cache["levels"][difficulty]["question"], mcq_cache["levels"][difficulty]["answer"], mcq_cache["levels"][difficulty]["context"], ""
            return mcq_cache["levels"][difficulty]["question"], ""

    else:
        return f"❌ 문제 생성 실패: {response.status_code}"

# NOTE: 함수 파라미터 변경 & 기능 수정정
# 문제 정답 확인 함수
def check_answer_with_gpt(difficulty, selected,citation):
    """
    correct = mcq_cache.get("correct", "")
    explanation = ""
    for line in mcq_cache.get("full", "").split("\n"):
        if line.startswith("해설:"):
            explanation = line.replace("해설:", "📝 해설:")
            break
    if selected.strip().lower() == correct.strip().lower():
        return f"✅ 정답입니다:)\n{explanation}"
    else:
        return f"❌ 오답입니다:(\n{explanation}"
    """
    if citation:
        url='<p>MLP 신경망 실습 강의: <a href="https://www.youtube.com/watch?v=qWslxdT3WjI" target="_blank">자세히 보기</a></p>'
    else:
        url=""

    difficulty_map = {"난이도 1": 0, "난이도 2": 1, "난이도 3": 2}
    difficulty = difficulty_map.get(difficulty, -1)
    level = mcq_cache["levels"].get(difficulty)
    answer = level["answer"]
    explanation = level["context"]

    if selected == answer:
        return "✅ 정답입니다 :)\n\n📝 해설: {}".format(explanation),url
    else:
        return "❌ 오답입니다 :(\n\n💡 정답: {}\n\n📝 해설: {}".format(answer, explanation),""