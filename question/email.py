from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pymongo import MongoClient
import os
import smtplib
from datetime import datetime, timezone, timedelta
from .review import get_due_review_events
import re
import base64
from collections import Counter
import matplotlib.pyplot as plt
from datetime import datetime
import os



# MongoDB setup (replace placeholders with your actual connection string and database details)
client = MongoClient("mongodb+srv://team9:1q2w3e4r!@6th-team9-2nd-db.global.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000")
db = client["6a013"]
collection = db["chat_logs"]
user_profiles = db["user_profiles"]

# 이메일 보내는 함수(추가)
def send_review_email_to_user(user_id):
    profile = db["user_profiles"].find_one({"user_id": user_id})
    if not profile or "email" not in profile:
        return "📭 이메일이 등록되어 있지 않습니다."

    email = profile["email"]
    due_events = get_due_review_events(user_id)

    if not due_events:
        return "💤 복습할 항목이 없습니다."

    subject = "📌 복습할 학습 항목이 있습니다!"
    body = "다음 항목들을 복습할 시간이에요:\n\n"
    for date, items in sorted(due_events.items()):
        body += f"📅 {date}\n"
        for item in items:
            body += f" - {item}\n"
        body += "\n"
    body += "Gradio에서 로그인하여 복습을 완료해보세요!"

    msg = MIMEMultipart()
    msg['From'] = os.getenv("GMAIL_USER")
    msg['To'] = email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(os.getenv("GMAIL_USER"), os.getenv("GMAIL_APP_PASSWORD"))
            server.send_message(msg)
        return f"✅ 전송 완료 ({email})"
    except Exception as e:
        return f"❌ 전송 실패: {e}"

# 피드백 보내는 함수(추가)
def send_feedback_email(user_id, feedback):
    sender = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_APP_PASSWORD")
    recipient = sender  # 관리자 본인에게 보냄

    subject = f"💡 사용자 피드백 도착 - {user_id}"
    body = f"""
📬 새로운 피드백이 도착했습니다!

👤 사용자: {user_id}
🕒 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}

💬 내용:
{feedback.strip()}
    """.strip()

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.send_message(msg)
        return "✅ 피드백이 관리자에게 전송되었습니다."
    except Exception as e:
        return f"❌ 메일 전송 실패: {e}"

# 피드백 저장 함수(추가)
def save_feedback(user_id, feedback):
    if not feedback.strip():
        return "❗ 피드백 내용을 입력해주세요."

    # MongoDB에 저장
    db["feedbacks"].insert_one({
        "user_id": user_id,
        "datetime": datetime.now(timezone.utc).isoformat(),
        "feedback": feedback.strip()
    })

    # 이메일 전송
    return send_feedback_email(user_id, feedback)

def notify_user_due_reviews(user_id):
    result = send_review_email_to_user(user_id)  # 이 함수는 기존에 있어야 함
    return f"{user_id} → {result}"

def notify_all_users_due_reviews():
    user_ids = db["user_profiles"].distinct("user_id")
    results = []
    for uid in user_ids:
        result = send_review_email_to_user(uid)
        results.append(f"{uid} → {result}")
    return "\n".join(results)

def validate_email_format(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def save_user_email(user_id, email):
    # 이메일 형식 검사
    if not validate_email_format(email):
        return "❌ 유효한 이메일 주소를 입력해주세요."

    # 이미 동일한 이메일이 저장되어 있는 경우 중복 저장 방지
    existing = user_profiles.find_one({"user_id": user_id})
    if existing and existing.get("email") == email:
        return "ℹ️ 이미 저장된 이메일입니다."

    # MongoDB에 저장 또는 업데이트
    user_profiles.update_one(
        {"user_id": user_id},
        {"$set": {"email": email}},
        upsert=True
    )
    return "✅ 이메일이 성공적으로 저장되었습니다."

def notify_wrapper(user_id):
    ADMIN_USERS = [ "admin"]
    if user_id in ADMIN_USERS:
        return notify_all_users_due_reviews()
    else:
        return "❌ 관리자만 실행할 수 있습니다."

def generate_admin_statistics():
    plt.rcParams.update({'axes.titlesize': 14, 'xtick.labelsize': 10, 'ytick.labelsize': 10})

    client = MongoClient(os.getenv("AZURE_COSMOSDB_CONNECTION_STRING"))
    db = client["6a013"]
    logs = list(db["chat_logs"].find({}))

    category_counter = Counter()
    user_counter = Counter()
    date_counter = Counter()

    for log in logs:
        # 카테고리 정제 처리
        raw_category = log.get("category", "없음")
        if isinstance(raw_category, dict):
            category = raw_category.get("subcategory_name") or raw_category.get("category_name") or "기타"
        else:
            category = str(raw_category)

        user = str(log.get("user_id", "unknown"))
        dt_str = log.get("datetime")
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            date_key = dt.date().isoformat()
        except:
            date_key = "unknown"

        category_counter[category] += 1
        user_counter[user] += 1
        date_counter[date_key] += 1

    top_n = 5
    common = category_counter.most_common(top_n)
    others_count = sum(count for cat, count in category_counter.items() if (cat, count) not in common)
    final_category_counter = dict(common)
    print("final_category_counter:",final_category_counter)

    if others_count > 0:
        final_category_counter["기타"] = others_count

    fig1, ax1 = plt.subplots(figsize=(6, 4))
    ax1.bar(final_category_counter.keys(), final_category_counter.values(), width=0.5)
    ax1.set_title("\U0001F4CA 카테고리별 학습 횟수 (Top 5 + 기타)")
    ax1.set_ylabel("횟수")
    ax1.set_xlabel("카테고리")
    ax1.tick_params(axis='x', rotation=30)
    ax1.grid(True, linestyle="--", alpha=0.5)

    fig2, ax2 = plt.subplots(figsize=(6, 4))
    ax2.bar(user_counter.keys(), user_counter.values(), width=0.5, color="orange")
    ax2.set_title("👤 사용자별 학습 횟수")
    ax2.set_ylabel("횟수")
    ax2.set_xlabel("사용자 ID")
    ax2.tick_params(axis='x', rotation=30)
    ax2.grid(True, linestyle="--", alpha=0.5)

    fig3, ax3 = plt.subplots(figsize=(6, 4))
    sorted_dates = sorted(date_counter.items())
    ax3.plot([d[0] for d in sorted_dates], [d[1] for d in sorted_dates], marker='o', linestyle='-', color='green')
    ax3.set_title("🗓️ 날짜별 학습량 추이")
    ax3.set_ylabel("질문 수")
    ax3.set_xlabel("날짜")
    ax3.tick_params(axis='x', rotation=45)
    ax3.grid(True, linestyle="--", alpha=0.5)
    print(sorted_dates)

    fig1.tight_layout()
    fig2.tight_layout()
    fig3.tight_layout()

    return fig1, fig2, fig3

