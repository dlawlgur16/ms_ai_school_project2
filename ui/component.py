import question
import gradio as gr
import random
import time
import os
from pymongo import MongoClient
from dotenv import load_dotenv
import json

import gpt
import question

load_dotenv()


def submit_message(history,user_id, message, max_tokens):
    chat_log = gpt.ask_gpt_answer_only(user_id, message, max_tokens)
    result=chat_log['answer']
    history.append([message, result])
    return chat_log,history , ""

def update_question_list(selected_keyword, cluster_state_str):
    """
    선택한 클러스터(키워드)에 해당하는 질문 목록을 업데이트합니다.
    입력으로 전달된 cluster_state_str을 JSON 문자열에서 dict로 복원한 후,
    해당 클러스터의 질문 목록(첫 번째 요소 q)만을 반환합니다.
    """
    cluster_state = json.loads(cluster_state_str)  # 문자열 → dict 복원
    return gr.update(choices=[q for q, _ in cluster_state[selected_keyword]], interactive=True)

def show_selected_answer(selected_question, cluster_state_str):
    """
    선택한 질문에 대한 답변을 반환합니다.
    입력으로 전달된 cluster_state_str을 JSON 문자열에서 dict로 복원하고,
    모든 클러스터에서 해당 질문(selected_question)에 대응하는 답변(a)을 찾아 반환합니다.
    """
    try:
        cluster_state = json.loads(cluster_state_str)  # 문자열을 dict로 복원
        for group in cluster_state.values():
            for q, a in group:
                if q == selected_question:
                    return a
        return "❌ 해당 질문의 답변을 찾을 수 없습니다."
    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"

def update_keywords_and_state():
    """
    question.cluster_questions() 함수를 호출하여 클러스터링 결과(키워드 목록, 상태 메시지,
    클러스터 데이터, 질문 리스트, 답변 리스트)를 받아옵니다.
    클러스터 데이터(state_map)는 JSON 문자열로 직렬화되어 반환됩니다.
    또한, 디버그용으로 클러스터 키워드와 state_map 내용을 파일에 기록합니다.
    """
    keywords, status, state_map, q_list, a_list = question.cluster_questions()

    try:
        with open("debug_cluster_keywords.log", "w", encoding="utf-8") as f:
            f.write("클러스터 키워드:\n")
            f.write(json.dumps(keywords, ensure_ascii=False, indent=2))
    except Exception as e:
        print("[DEBUG] 클러스터 키워드 저장 실패:", e)

    try:
        with open("debug_state_map.log", "w", encoding="utf-8") as f:
            f.write("state_map 내용:\n")
            f.write(json.dumps(state_map, ensure_ascii=False, indent=2))
    except Exception as e:
        print("[DEBUG] state_map 저장 실패:", e)

    print("[DEBUG] 상태 메시지:", status.encode("ascii", "ignore").decode(errors="ignore"))
    print("[DEBUG] state_map 타입:", type(state_map))
    print("[DEBUG] state_map 길이:", len(state_map))
    print("state_map → debug_state_map.log 저장 완료")

    # state_map이 dict이면 JSON 문자열로 변환하고, 그렇지 않으면 빈 JSON 객체를 반환
    state_map_json = json.dumps(state_map, ensure_ascii=False) if isinstance(state_map, dict) else "{}"

    return (
        gr.update(choices=keywords, interactive=True),
        gr.update(value=status),
        state_map_json,  # 문자열로 변환해서 저장!
        q_list,
        a_list
    )

def load_combined():
    """
    question 모듈의 load_recent_questions와 load_all_questions_summary 함수를 호출하여,
    최근 질문과 전체 질문 요약 데이터를 함께 반환합니다.
    """
    return question.load_recent_questions(), question.load_all_questions_summary()





def toggle_inputs(kmeans, similarity):
        return (
            gr.update(visible=kmeans),
            gr.update(visible=similarity)
        )

def run_clustering(kmeans, similarity, n, threshold):
    client = MongoClient(os.getenv("AZURE_COSMOSDB_CONNECTION_STRING"))
    db = client["6a013"]
    collection = db["chat_logs_yj"]
    if not kmeans and not similarity:
        return "❗ 클러스터링 방법을 선택해주세요.", gr.update(visible=False), gr.update(visible=False), {}, []

    k_keys, s_keys, combined_map = [], [], {}
    if kmeans:
        k_keys, _, k_map = question.cluster_questions_kmeans(n)
        combined_map.update({f"[KMeans] {k}": v for k, v in k_map.items()})
        for keyword, qapairs in k_map.items():
            for query, _ in qapairs:
                doc = collection.find_one({"query": query})
                if doc:
                    collection.update_one({"_id": doc["_id"]}, {"$set": {"category_kmeans": keyword}})

    if similarity:
        s_keys, _, s_map = question.cluster_questions_similarity(threshold)
        combined_map.update({f"[Similarity] {k}": v for k, v in s_map.items()})
        for keyword, qapairs in s_map.items():
            for query, _ in qapairs:
                doc = collection.find_one({"query": query})
                if doc:
                    collection.update_one({"_id": doc["_id"]}, {"$set": {"category_similarity": keyword}})

    return (
        "✅ 모든 클러스터링 및 DB 업데이트 완료",
        gr.update(choices=[f"[KMeans] {k}" for k in k_keys], visible=kmeans),
        gr.update(choices=[f"[Similarity] {s}" for s in s_keys], visible=similarity),
        combined_map,
        gr.update(choices=[], value=None)
    )

def update_questions(selected_keyword, state):
        if selected_keyword in state:
            questions = [q for q, _ in state[selected_keyword]]
            return gr.update(choices=questions, value=questions[0] if questions else None)
        return gr.update(choices=[], value=None)

def show_answer(selected_question, state):
        for q_list in state.values():
            for q, a in q_list:
                if q == selected_question:
                    return a
        return "❌ 해당 질문의 답변을 찾을 수 없습니다."
