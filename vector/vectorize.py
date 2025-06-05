import os
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables (requires a `.env` file with proper keys)
load_dotenv()

client = MongoClient("mongodb+srv://team9:1q2w3e4r!@6th-team9-2nd-db.global.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000")
db = client["6a013"]
collection = db["chat_logs"]
azure_textembedding_endpoint = os.getenv("AZURE_TEXTEMBEDDING_ENDPOINT")
azure_textembedding_key = os.getenv("AZURE_TEXTEMBEDDING_KEY")


# 벡터화 함수
def vectorize(query):
    embedding_endpoint = os.getenv("AZURE_TEXTEMBEDDING_ENDPOINT")
    embedding_key = os.getenv("AZURE_TEXTEMBEDDING_KEY")
    headers = {
        "Content-Type": "application/json",
        "api-key": embedding_key
    }
    payload = {
        "input": query,
        "model": "text-embedding-ada-002"
    }
    response = requests.post(
    url=embedding_endpoint,
    headers=headers,
    json=payload
    )

    if response.status_code == 200:
        vector = response.json()["data"][0]["embedding"]
        print("✅ Embedding created.")
        return vector
    else:
        print(f"❌ Embedding API Error: {response.status_code}")
        print(response.text)
        return

def vectorize_upload(chat_log):

    # MongoDB 연결
    client = MongoClient(os.getenv("AZURE_COSMOSDB_CONNECTION_STRING"))
    db = client["6a013"]
    collection = db["chat_logs"]
    print('chat_log: ',chat_log)
    vector=vectorize(chat_log["query"])


    log = {
        "user_id": chat_log["user_id"],
        "datetime": chat_log["datetime"],
        "query": chat_log["query"],
        "answer": chat_log["answer"],
        "summary": chat_log["summary"],
        "category": {
            "category_name": chat_log["category"]["category_name"],
            "subcategory_name": chat_log["category"]['subcategory_name']
        },
        "query_vectorized": vector
    }
    print(log)

    collection.insert_one(log)
    return "성공적으로 저장되었습니다."

# 벡터화(RAG) 함수
def vectorize_upload_rag(chat_log):
    # MongoDB 연결
    client = MongoClient(os.getenv("AZURE_COSMOSDB_CONNECTION_STRING"))
    db = client["6a013"]
    collection = db["chat_logs"]
    print('chat_log: ',chat_log)
    if not chat_log.get('query_vectorized', False):
        print("query_vectorized가 비어있습니다.")
        vector=vectorize(chat_log["query"])
    else:
        vector=chat_log.get('query_vectorized')
    log = {
        "user_id": chat_log["user_id"],
        "datetime": chat_log["datetime"],
        "query": chat_log["query"],
        "answer": chat_log["answer"],
        "summary": chat_log["summary"],
        "timestamps": chat_log["timestamps"],
        "category": {
            "category_name": chat_log["category"]["category_name"],
            "subcategory_name": chat_log["category"]['subcategory_name']
        },
        "query_vectorized": vector
    }
    print(log)
    collection.insert_one(log)
    return "성공적으로 저장되었습니다."