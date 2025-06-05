# Import necessary libraries
import os
import re
import requests
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv


from .gpt_answer import ask_gpt_answer_only
from .gpt_answer import process_user_query
from .gpt_answer import initialize_database
import vector

# Load environment variables (requires a `.env` file with proper keys)
load_dotenv()

# Azure OpenAI and other service credentials
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

# 사용자 쿼리를 평가하고 적합한 카테고리에 추가
def classify_and_append_query(query):
    categories_collection= initialize_database("6a055","category_classified")
    query_embedding = vector.vectorize(query)

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

    return category_name, subcategory_name,query_embedding

# 함수 선언
def ask_gpt_rag(user_id, query):
    # endpoint, headers, body 변수 만들기
    endpoint = azure_oai_endpoint
    headers = {
        "Content-Type": "application/json",
        "api-key": azure_oai_key
    }

    body = {
        "messages": [
            {
                "role": "user",
                "content": query
            }
        ],
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 800,
        "data_sources": [
            {
                "type": "azure_search",
                "parameters": {
                    "endpoint": azure_search_endpoint,
                    "index_name": "vector-yj-test-2",
                    "semantic_configuration": "vector-yj-test-2-semantic-configuration",
                    "query_type": "semantic",
                    "fields_mapping": {},
                    "in_scope": True,
                    "role_information": "",
                    "filter": None,
                    "strictness": 1,
                    "top_n_documents": 1,
                    "authentication": {
                        "type": "api_key",
                        "key": azure_search_key
                    },
                    "key": azure_search_key,
                    "indexName": "vector-yj-test-2"
                }
            }
        ]
    }
    ta_credential = AzureKeyCredential(azure_services_key)
    client = TextAnalyticsClient(
        endpoint=azure_services_endpoint,
        credential=ta_credential)
    # 응답 요청
    response = requests.post(endpoint, headers=headers, json=body)

    # 200 OK
    if response.status_code == 200:
        response_json = response.json()
        answer = response_json["choices"][0]["message"]["content"]
        if ("The requested information is not" in answer
                or "요청된 정보" in answer
                or "찾을 수 없습니다" in answer):
            print("answer:",answer)
            rag_log=ask_gpt_answer_only(user_id,query)
            return rag_log, ""
        unix_time = response_json['created']
        KST = timezone(timedelta(hours=9))
        dt = datetime.fromtimestamp(unix_time, tz=KST)
        poller = client.begin_abstract_summary([answer], sentence_count=1, language="ko")
        summary = ""
        abstract_summary_results = poller.result()
        for result in abstract_summary_results:
            if result.kind == "AbstractiveSummarization":
                for content in result.summaries:
                    summary += content.text
            elif result.is_error is True:
                print("...Is an error with code '{}' and message '{}'".format(result.error.code, result.error.message))

        citations = response_json["choices"][0]["message"]["context"]["citations"]
        category_name,subcategory_name,vector=classify_and_append_query(query)
        timestamps = []
        for citation in citations:
            content = citation.get("content", "")
            # 정규식으로 timestamp 패턴 추출
            found = re.findall(r'"timestamp":\s*"([^"]+)"', content)
            timestamps.extend(found)

        rag_log = {
            "user_id": user_id,
            "datetime": dt.isoformat(),  # ISO 8601 문자열로 저장 (MongoDB에서 타임스탬프로 자동 인식)
            "query": query,
            "answer": answer,
            "summary": summary,
            "timestamps": timestamps,
            "category": {
                "category_name": category_name,
                "subcategory_name": subcategory_name
            },
            "query_vectorized": vector
        }

        print(response_json)

        view_points = ""
        # print("📌 관련 타임스탬프:")

        for ts in timestamps:
            print("-", ts)
            view_points += f"{ts}\n"

        return rag_log,view_points
    else:
        return response.status_code, ""

def convert_timestamp_to_seconds(timestamp):
    """타임스탬프를 초 단위로 변환 (00:00:00 형식)"""
    parts = timestamp.split(':')
    if len(parts) == 2:  # MM:SS 형식
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:  # HH:MM:SS 형식
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0

def create_youtube_timestamp_link(timestamp, video_id="UwA8gp-7oeY"):
    """타임스탬프로 유튜브 링크 생성"""
    # 범위에서 첫 번째 타임스탬프 추출 (예: "00:22:12 ~ 00:23:30" -> "00:22:12")
    match = re.search(r"(\d{2}:\d{2}:\d{2}|\d{2}:\d{2})", timestamp)
    if match:
        start_time = match.group(1)
        seconds = convert_timestamp_to_seconds(start_time)
        return f"https://www.youtube.com/watch?v={video_id}&t={seconds}s"
    return f"https://www.youtube.com/watch?v={video_id}"

def update_timestamp_buttons(view_points):
    """타임스탬프 텍스트를 스타일이 적용된 HTML 버튼으로 변환"""
    if not view_points:
        return ""
    # view_points가 문자열일 때 처리
    if isinstance(view_points, str):
        timestamp_list = view_points.strip().split('\n')
    # view_points가 리스트일 때 처리
    elif isinstance(view_points, list):
        timestamp_list = [str(item).strip() for item in view_points]



    # 버튼 출력용 (HTML에 표시)
    buttons_html = "<div style='margin-top: 10px;'>"

    for ts in timestamp_list:
        if ts.strip():  # 빈 줄 건너뛰기
            link = create_youtube_timestamp_link(ts)
            # 스타일이 적용된 버튼 HTML 생성
            buttons_html += f"""
            <a href="{link}" target="_blank" style="
                display: inline-block;
                margin: 5px;
                padding: 8px 15px;
                background-color: #4285f4;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                font-weight: bold;
                cursor: pointer;
            ">{ts}</a>
            """

    buttons_html += "</div>"
    return buttons_html

# 쿼리를 받으면 citation을 URL로 반환하는 함수
def gpt_ask_gpt_rag_image(query):
    endpoint = azure_oai_endpoint
    headers = {
        "Content-Type": "application/json",
        "api-key": azure_oai_key
    }

    body = {
        "data_sources": [
            {
                "type": "azure_search",
                "parameters": {
                    "endpoint": azure_search_endpoint,
                    "index_name": "pdf-indexer",
                    "semantic_configuration": "pdf-image-semantic",
                    "query_type": "semantic",
                    "fields_mapping": {},
                    "in_scope": True,
                    "role_information": "",
                    "filter": None,
                    "strictness": 3,
                    "top_n_documents": 5,
                    "authentication": {
                        "type": "api_key",
                        "key": azure_search_key
                    }
                }
            }
        ],
        "messages": [
            {
                "role": "user",
                "content": query
            }
        ],
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 800,
        "stream": False,
        "frequency_penalty": 0,
        "presence_penalty": 0
    }

    response = requests.post(endpoint, headers=headers, json=body)

    if response.status_code != 200:
        print(f"API 호출 실패: {response.status_code}, {response.text}")
        return None

    data = response.json()
    citations = []

    try:
        context = data["choices"][0]["message"]["context"]
        raw_citations = context.get("citations", [])

        for citation in raw_citations:
            content = citation.get("content", "")
            urls = re.findall(r"https:\/\/[^\s]+?\.png", content)
            citations.extend(urls)

        if not citations:
            return None
        return citations

    except Exception as e:
        print("에러 발생:", e)
        return "None"

# 이미지 URL을 HTML로 변환하는 함수
def render_image_gallery_html(urls: list[str]) -> str:
    if not urls:
        return "<p><i>관련 이미지가 없습니다.</i></p>"

    gallery_html = "<div style='display: flex; flex-wrap: wrap; gap: 10px;'>"
    for url in urls:
        gallery_html += f"""
        <div style="border:1px solid #ddd; padding:4px;">
            <img src="{url}" style="width:180px; border-radius:4px;" alt="image"/>
        </div>
        """
    gallery_html += "</div>"
    return  gallery_html

def gpt_ask_gpt_rag_answer_only(user_id, query):
    urls = gpt_ask_gpt_rag_image(query)
    gallery_html = render_image_gallery_html(urls)
    chat_log, citation = ask_gpt_rag(user_id=user_id, query=query)
    answer = chat_log['answer']
    timestamp_buttons = update_timestamp_buttons(citation)
    return answer, chat_log, timestamp_buttons, gallery_html