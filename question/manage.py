# Import necessary libraries
import os
from pymongo import MongoClient
import gradio as gr  # Gradio interface for interactive functionalities
from dotenv import load_dotenv
from bson import ObjectId

# Load environment variables (requires a `.env` file with proper keys)
load_dotenv()

# MongoDB setup (replace placeholders with your actual connection string and database details)
client = MongoClient("mongodb+srv://team9:1q2w3e4r!@6th-team9-2nd-db.global.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000")
db = client["6a013"]
collection = db["chat_logs"]

# 개인 질문 로딩 함수
def load_questions(user_id):
    docs = list(collection.find({"user_id": user_id}))
    display_list = [
        (f"[{doc.get('category', {}).get('category_name', '기타')}] {doc['query'][:20]}...", str(doc["_id"])) for doc in docs
    ]
    return gr.update(choices=display_list), docs

# 질문 삭제 함수
def delete_question(selected_id, docs):
    try:
        obj_id = ObjectId(selected_id)
    except Exception as e:
        return gr.update(choices=[]), [], f"삭제 오류: {e}", "", "", gr.update(visible=False)
    collection.delete_one({"_id": obj_id})
    return gr.update(choices=[]), [], "", "", "", gr.update(visible=False)
