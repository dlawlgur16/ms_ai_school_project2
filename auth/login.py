import gradio as gr
from pymongo import MongoClient




def check_login(username, password):
    client = MongoClient("mongodb+srv://team9:1q2w3e4r!@6th-team9-2nd-db.global.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000")
    db = client["6b006"]
    collection = db["userdata"]
    user = collection.find_one({"id": username, "pw": password})


    if user:  # 사용자 정보가 존재할 경우
        # 사용자가 'admin'일 경우
        if user["id"] == "admin":
            return (
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=True),
                username,username,username # 로그인 성공 시 사용자 이름 반환
            )
        else:
            return (
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=False),
                username,username,username # 로그인 성공 시 사용자 이름 반환
            )
    else:  # 로그인 실패
        return (
            gr.update(visible=True),    # 첫 번째 column (로그인 실패 시 보임)
            gr.update(visible=False),
            gr.update(visible=False),# 두 번째 column (로그인 성공 시 숨김)
            "❌ 로그인 실패. 다시 시도해주세요.",  # 로그인 실패 메시지
            ""  # 실패 시 추가 데이터 없음
        )