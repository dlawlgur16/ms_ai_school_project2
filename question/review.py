# Import necessary libraries
import os
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
import gradio as gr
from dotenv import load_dotenv
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
from bson import ObjectId
import calendar
import matplotlib.pyplot as plt
from matplotlib import rcParams
import re

import gpt
from vector.vectorize import vectorize

# Load environment variables (requires a `.env` file with proper keys)
load_dotenv()

# MongoDB setup (replace placeholders with your actual connection string and database details)
client = MongoClient("mongodb+srv://team9:1q2w3e4r!@6th-team9-2nd-db.global.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000")
db = client["6a013"]
collection = db["chat_logs"]

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지



# ✅ SM2 알고리즘 직접 구현  ( 추가 )
class SM2:
    def __init__(self, ease=2.5, interval=1, repetitions=0):
        self.ease = ease
        self.interval = interval
        self.repetitions = repetitions

    def review(self, quality):
        if quality < 3:
            self.repetitions = 0
            self.interval = 1
        else:
            if self.repetitions == 0:
                self.interval = 1
            elif self.repetitions == 1:
                self.interval = 6
            else:
                self.interval = round(self.interval * self.ease)

            self.repetitions += 1
            self.ease += 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
            if self.ease < 1.3:
                self.ease = 1.3

        return self


def save_generated_question(user_id, question_text,check_result):
    question_collection = db["question_logs"]
    print(user_id,"question_text: ", question_text,"opt_radio: ",check_result)

    def extract_question(question_text):
        match = re.search(r"문제:\s*(.*?)(?=\na\)|\b$)", question_text)  # '문제: ' 뒤에 나오는 텍스트 추출
        if match:
            return match.group(1)
        else:
            return None
    question = extract_question(question_text)
    vector=vectorize( question)

    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "query": question_text,
        "query_vectorized": vector,
        "answer": check_result,  # 사용자가 나중에 답변을 추가할 수도 있음
        "review_counts": 0,
        "repetitions": 0,
        "interval": 1,
        "ease": 2.5,
        "datetime": now.isoformat(),
        "review_date": now.isoformat(),
        "next_review": (now + timedelta(days=1)).isoformat()
    }
    question_collection.insert_one(doc)
    print("✅ GPT 생성 문제가 복습 목록에 저장되었습니다.")
    return


# 복습 횟수 적용 함수 ( 수정 )
def complete_review(selected_id, docs, quality=4):
    doc = next((d for d in docs if str(d['_id']) == selected_id), None)
    if not doc:
        return "", "", "", "", gr.update(visible=False), None

    now = datetime.now(timezone.utc)

    repetitions = doc.get("repetitions", 0)
    interval = doc.get("interval", 1)
    ease = doc.get("ease", 2.5)

    sm2 = SM2(ease=ease, interval=interval, repetitions=repetitions)
    updated = sm2.review(quality=quality)
    next_review = now + timedelta(days=updated.interval)

    collection.update_one(
        {"_id": doc["_id"]},
        {"$set": {
            "review_counts": repetitions + 1,
            "repetitions": updated.repetitions,
            "interval": updated.interval,
            "ease": updated.ease,
            "review_date": now.isoformat(),
            "next_review": next_review.isoformat()
        }}
    )

    updated_doc = collection.find_one({"_id": doc["_id"]})
    for i, d in enumerate(docs):
        if str(d["_id"]) == selected_id:
            docs[i] = updated_doc

    return show_question_details(selected_id, docs)





def show_question_details(selected_id, docs):
    doc = next((d for d in docs if str(d['_id']) == selected_id), None)
    if not doc:
        return "", "", "", "", gr.update(visible=False), None

    now = datetime.now(timezone.utc)
    review_date = doc.get("review_date")
    next_review = doc.get("next_review")
    repetitions = doc.get("repetitions", 0)
    timestamps = gpt.update_timestamp_buttons(doc.get("timestamps", []))

    status_lines = [f"📚 복습 횟수: {repetitions}회"]
    if review_date:
        status_lines.append(f"🗓 마지막 복습: {review_date}")
    if next_review:
        next_dt = datetime.fromisoformat(next_review)
        delta = next_dt - now
        if delta.total_seconds() > 0:
            status_lines.append(f"⏳ 다음 복습까지 남은 시간: {str(delta).split('.')[0]}")
        else:
            status_lines.append("⚠️ 복습 시점이 지났습니다!")

    show_delete = gr.update(visible=(repetitions >= 5))

    return doc["query"], doc["answer"], doc["summary"], "<br>".join(status_lines), show_delete, timestamps


### 🔹 질문 클릭 시 답변 + 요약 출력
def get_answer_summary(query_label):
    query = query_label.split(" (")[0]  # 타임스탬프 제거
    doc = collection.find_one({"query": query})
    print("doc :",doc)
    print("query : ",query)

    if not doc:
        return "❗ 해당 질문에 대한 답변이 없습니다."

    summary = doc.get("summary", "")
    answer = doc.get("answer", "")
    return f"[요약]\n{summary}\n\n[전체 답변]\n{answer}"


# 사용자의 복습 예정 항목을 날짜별로 정리 함수( 수정 )
def get_due_review_events(user_id, days=30):
    today = datetime.now().date()
    events = defaultdict(list)

    docs = list(collection.find({"user_id": user_id}))
    for doc in docs:
        next_review = doc.get("next_review")
        if not next_review:
            continue
        due_time = datetime.fromisoformat(next_review)
        due_date = due_time.date()
        if today <= due_date < today + timedelta(days=days):
            events[due_date.strftime("%Y-%m-%d")].append("복습: " + doc["query"][:30] + "...")
    return events









