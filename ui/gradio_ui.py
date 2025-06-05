import gradio as gr
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from pymongo import MongoClient
import matplotlib.pyplot as plt
import random
import time

#모듈화
import auth
import gpt
import vector
import question
from ui import component
from ui import css
from question import email  # email.py 안에 있는 함수 가져오기




def create_demo():
    with gr.Blocks(theme="soft") as demo:
        login_box = gr.Column(visible=True)
        chatbot_user_ui = gr.Column(visible=False)
        chatbot_admin_ui = gr.Column(visible=False)

        with login_box:
            gr.Markdown("### 🔐 로그인")
            username = gr.Textbox(label="아이디")
            password = gr.Textbox(label="비밀번호", type="password")
            login_btn = gr.Button("로그인")
            user_state = gr.State()

        with chatbot_user_ui:
            with gr.Tab("QnA"):
                gr.Markdown("## 🤖 GPTutor")
                gr.Markdown("무엇이든 답해드립니다.")
                user_id = gr.Textbox(label="Current User", interactive=False)
                history =gr.State([])
                answer_state = gr.State()
                # 채팅 인터페이스
                chatbot = gr.Chatbot(height=500)

                with gr.Row(equal_height=True):
                    message = gr.Textbox(
                        placeholder="질문을 입력하세요",
                        label=None,
                        container=False,
                        scale=8
                    )
                    submit_btn = gr.Button("Send", scale=1)

                # 추천문구 버튼과 토큰 슬라이더
                with gr.Row():
                    ex1 = gr.Button("예시: 임베디드가 뭐야?", scale=1)
                    ex2 = gr.Button("예시: 리스트 컴프리헨션 설명해줘", scale=1)
                    ex3 = gr.Button("예시: 파이썬 모듈이란?", scale=1)
                    token_slider = gr.Slider(
                        minimum=100,
                        maximum=1500,
                        value=300,
                        step=50,
                        label="답변 길이",
                        container=False,
                        scale=1
                    )

                # 저장 버튼
                save_btn = gr.Button("Save")
                save_result = gr.Textbox(label="저장 결과", interactive=False)



                message.submit(
                    fn=component.submit_message,
                    inputs=[history,user_id, message, token_slider],
                    outputs=[chatbot, message]
                )
                save_btn.click(fn=vector.vectorize_upload, inputs=[answer_state], outputs=[save_result])
                submit_btn.click(fn=component.submit_message, inputs=[history,user_id, message, token_slider], outputs=[answer_state,chatbot, message])
                ex1.click(lambda: "임베디드가 뭐야?", None, message)
                ex2.click(lambda: "리스트 컴프리헨션 설명해줘", None, message)
                ex3.click(lambda: "파이썬 모듈이란?", None, message)

            with gr.Tab("QnA_RAG"):
                gr.Markdown("## 🤖 GPTutor")
                gr.Markdown("무엇이든 답해드립니다.")
                user_id1 = gr.Textbox(label="Current User", interactive=False)
                result_text = gr.Textbox(label='GPTutor for you')
                citation = gr.HTML(label="View Points")
                gallery_html = gr.HTML(label=None)
                with gr.Row(equal_height=True):
                    message = gr.Textbox(placeholder="질문을 입력하세요", label=None, scale=9)
                    submit_btn = gr.Button("Send", scale=1)
                    answer_state = gr.State()
                save_btn = gr.Button("Save")
                save_result = gr.Textbox(label="저장 결과", interactive=False)

                submit_btn.click(fn=gpt.gpt_ask_gpt_rag_answer_only, inputs=[user_id1, message], outputs=[result_text, answer_state, citation, gallery_html])
                save_btn.click(fn=vector.vectorize_upload_rag, inputs=[answer_state], outputs=[save_result])

            with gr.Tab("📘 Personal Review"):
                load_btn = gr.Button("📂 불러오기")
                question_list = gr.Radio(label="📚 질문 목록", choices=[], interactive=True)
                question_data = gr.State([])
                query = gr.Textbox(label="❓ 질문 내용", lines=2)
                answer = gr.Textbox(label="💬 답변", lines=3)
                summary = gr.Textbox(label="📝 요약", lines=2)
                citation = gr.HTML(label="View Points")
                status = gr.Markdown(label="🔄 복습 상태")
                review_btn = gr.Button("✅ 복습 완료")
                delete_btn = gr.Button("🗑️ 복습 항목 삭제", visible=False)


                gr.Markdown("### 기억난 정도 선택")
                with gr.Row():
                    btn_easy = gr.Button("✅ 잘 기억남 (5)")
                    btn_okay = gr.Button("🤔 애매하게 기억남 (3)")
                    btn_hard = gr.Button("😵 기억 안남 (2)")
                feedback = gr.HTML(value="", visible=True)

                btn_easy.click(
                    lambda ql, qd: question.complete_review(ql, qd, 5),
                    inputs=[question_list, question_data],
                    outputs=[query, answer, summary, status, delete_btn]
                ).then(lambda: "<span style='color:green; font-weight:bold;'>✅ 복습 저장 완료!</span>", None, feedback)
                btn_okay.click(
                    lambda ql, qd: question.complete_review(ql, qd, 3),
                    inputs=[question_list, question_data],
                    outputs=[query, answer, summary, status, delete_btn]
                ).then(lambda: "<span style='color:green; font-weight:bold;'>✅ 복습 저장 완료!</span>", None, feedback)
                btn_hard.click(
                    lambda ql, qd: question.complete_review(ql, qd, 1),
                    inputs=[question_list, question_data],
                    outputs=[query, answer, summary, status, delete_btn]
                ).then(lambda: "<span style='color:green; font-weight:bold;'>✅ 복습 저장 완료!</span>", None, feedback)

                gr.Markdown("---")
                # GPT 문제 생성 영역 + 복습 문제 난이도 선택 추가
                gr.Markdown("### 복습 문제 생성 및 난이도 선택")
                # 복습 문제 난이도 선택용 라디오
                difficulty_radio = gr.Radio(choices=["난이도 1", "난이도 2", "난이도 3"], label="복습 문제 난이도 선택")

                gen_btn = gr.Button("🧠 GPT 문제 생성")
                mcq_output = gr.Textbox(label="📋 생성된 문제", lines=6, interactive=False)
                opt_radio = gr.Radio(["a", "b", "c", "d"], label="정답 선택")

                with gr.Row():
                    check_btn = gr.Button("✅ 정답 확인")
                    gen_add_btn = gr.Button("다음 문제 풀기")

                check_result = gr.Textbox(label="결과 피드백", interactive=False)
                redirect_to_url = gr.HTML()
                gr.Markdown("---")

                stats_plot = gr.Plot()

                # GPT 문제 생성 시 입력에 문제 난이도를 포함
                gen_btn.click(fn=gpt.create_gpt, inputs=[difficulty_radio, query, answer], outputs=[mcq_output, check_result])
                gen_add_btn.click(fn=gpt.create_gpt, inputs=[difficulty_radio, query, answer], outputs=[mcq_output, check_result])
                question_list.change(
                    fn=question.show_question_details,
                    inputs=[question_list, question_data],
                    outputs=[query, answer, summary, status, delete_btn, citation]
                )
                delete_btn.click(
                    fn=question.delete_question,
                    inputs=[question_list, question_data],
                    outputs=[question_list, question_data, query, answer, summary, delete_btn]
                )

                load_btn.click(question.load_questions, inputs=[user_id], outputs=[question_list, question_data])
                load_btn.click(question.get_stats, inputs=[user_id], outputs=stats_plot)

                review_btn.click(question.complete_review, inputs=[question_list, question_data], outputs=[query, answer, summary, status, delete_btn])
                check_btn.click(fn=gpt.check_answer_with_gpt, inputs=[difficulty_radio,opt_radio,citation], outputs=[check_result,redirect_to_url])
                check_btn.click(fn=question.save_generated_question, inputs=[user_id, mcq_output, check_result], outputs=[])

            with gr.Tab("🕒 Review Together"):
                gr.Markdown("### 🆕 최근 질문 20선 (가장 최근 순)")
                load_btn = gr.Button("📥 불러오기")

                with gr.Row():
                    recent_radio = gr.Radio(label="❓ 질문을 클릭하세요", choices=[], interactive=True)
                    recent_answer = gr.Textbox(label="📘 답변 요약 및 전체 보기", lines=10, interactive=False)

                gr.Markdown("---")
                gr.Markdown("### 📋 전체 질문 요약 리스트 (최신순)")

                all_questions_table = gr.Dataframe(
                    headers=["질문", "요약", "시간"],
                    interactive=False,
                    wrap=True,
                )


                load_btn.click(fn=component.load_combined,
                               outputs=[recent_radio, all_questions_table])

                # 선택된 질문 → 답변 표시
                recent_radio.change(fn=question.get_answer_summary,
                                    inputs=recent_radio,
                                    outputs=recent_answer)


            with gr.Tab("📅 Calendar & Goals"):
                gr.Markdown("### 📆 복습 캘린더")
                calendar_overview = gr.Plot(label="복습 예정 이벤트")
                refresh_calendar_btn = gr.Button("캘린더 새로고침")

                gr.Markdown("### 🔔 복습 알림 확인")
                review_alert = gr.Textbox(label="복습 알림", interactive=False)
                check_review_btn = gr.Button("복습 알림 확인")

                # ✅ 버튼 이벤트 연결
                refresh_calendar_btn.click(fn=css.generate_calendar_overview, inputs=[user_id], outputs=calendar_overview)
                check_review_btn.click(fn=css.check_due_reviews, inputs=[user_id], outputs=review_alert)

            with gr.Tab("📬 Email Settings"):
                gr.Markdown("### 📮 복습 알림 이메일 등록")

                #if gpt.initialize_database('6a013','user_profiles').find_one({"user_id": user_id}):
                email_input = gr.Textbox(label="이메일 주소", placeholder="your@email.com")
                save_email_btn = gr.Button("이메일 저장")
                save_result = gr.Textbox(label="저장 결과", interactive=False)
                save_email_btn.click(fn=question.save_user_email, inputs=[user_id, email_input], outputs=save_result)

                gr.Markdown("### 📨 내 복습 메일 수동 전송 (개인용)")
                my_review_btn = gr.Button("📨 내 복습 메일 받기")
                my_review_result = gr.Textbox(label="전송 결과", interactive=False)
                my_review_btn.click(fn=question.notify_user_due_reviews, inputs=[user_id], outputs=my_review_result)

                gr.Markdown("### 💡 피드백 보내기")
                feedback_input = gr.Textbox(label="피드백", placeholder="건의사항이나 개선 요청을 자유롭게 적어주세요!", lines=4)
                send_feedback_btn = gr.Button("📤 피드백 전송")
                feedback_result = gr.Textbox(label="결과", interactive=False)
                send_feedback_btn.click(fn=question.save_feedback, inputs=[user_id, feedback_input], outputs=feedback_result)

        with chatbot_admin_ui:
            with gr.Tab("📊 Instructor Insights"):
                gr.Markdown("## 📊 질문 클러스터 통계 및 분석")

                kmeans_check = gr.Checkbox(label="📌 KMeans Clustering")
                similarity_check = gr.Checkbox(label="📌 Similarity Based Clustering")
                n_clusters_slider = gr.Slider(2, 10, step=1, label="KMeans 클러스터 수", visible=False)
                similarity_slider = gr.Slider(0, 1, step=0.05, label="Similarity Threshold", visible=False)
                run_button = gr.Button("🔍 클러스터링 실행")
                status = gr.Textbox(label="상태", interactive=False)

                with gr.Row():
                    kmeans_keywords = gr.Radio(label="KMeans 키워드 그룹", choices=[], visible=False)
                    similarity_keywords = gr.Radio(label="Similarity 키워드 그룹", choices=[], visible=False)

                question_list = gr.Radio(label="질문 목록", choices=[], interactive=True)
                selected_answer = gr.Textbox(label="답변", lines=5, interactive=False)
                cluster_state = gr.State()



                kmeans_check.change(fn=component.toggle_inputs, inputs=[kmeans_check, similarity_check], outputs=[n_clusters_slider, similarity_slider])
                similarity_check.change(fn=component.toggle_inputs, inputs=[kmeans_check, similarity_check], outputs=[n_clusters_slider, similarity_slider])




                run_button.click(
                    fn=component.run_clustering,
                    inputs=[kmeans_check, similarity_check, n_clusters_slider, similarity_slider],
                    outputs=[status, kmeans_keywords, similarity_keywords, cluster_state, question_list]
                )



                kmeans_keywords.change(fn=component.update_questions, inputs=[kmeans_keywords, cluster_state], outputs=question_list)
                similarity_keywords.change(fn=component.update_questions, inputs=[similarity_keywords, cluster_state], outputs=question_list)



                question_list.change(fn=component.show_answer, inputs=[question_list, cluster_state], outputs=selected_answer)

                gr.Markdown("## 📊 KMeans / Similarity 질문 통계 (Basic vs Advanced)")

                stat_button = gr.Button("📊 통계 시각화 생성")

                with gr.Row():
                    kmeans_plot = gr.Plot(label="KMeans 카테고리별 질문 수")
                    sim_plot = gr.Plot(label="Similarity 카테고리별 질문 수")

                with gr.Row():
                    kmeans_time_plot = gr.Plot(label="KMeans 시간대별 질문 수")
                    sim_time_plot = gr.Plot(label="Similarity 시간대별 질문 수")

                stat_button.click(
                    fn=question.generate_kmeans_similarity_statistics,
                    inputs=[],
                    outputs=[
                        kmeans_plot, sim_plot,
                        kmeans_time_plot, sim_time_plot
                    ]
                )
                gr.Markdown("## 📊 GPTutor 교수자 리포트 생성기")

                with gr.Row():
                    generate_btn = gr.Button("📄 리포트 생성")
                    open_btn = gr.Button("🌐 리포트 열기")

                status = gr.Textbox(label="상태 메시지", interactive=False)
                generate_btn.click(fn=question.generate_html_report, outputs=[status])
                open_btn.click(fn=question.open_report_in_browser, outputs=[status])


            with gr.Tab("📬 Email Settings"):
                gr.Markdown("### 📮 복습 알림 이메일 등록")

                gr.Markdown("### 📢 복습 알림 수동 전송 (관리자용)")
                notify_btn = gr.Button("📤 복습 알림 일괄 전송")
                notify_result = gr.Textbox(label="전송 결과", interactive=False)
                notify_btn.click(fn=question.notify_wrapper, inputs=[user_id], outputs=notify_result)

                gr.Markdown("### 💡 피드백 보내기")
                feedback_input = gr.Textbox(label="피드백", placeholder="건의사항이나 개선 요청을 자유롭게 적어주세요!", lines=4)
                send_feedback_btn = gr.Button("📤 피드백 전송")
                feedback_result = gr.Textbox(label="결과", interactive=False)
                send_feedback_btn.click(fn=question.save_feedback, inputs=[user_id, feedback_input], outputs=feedback_result)



        login_btn.click(fn=auth.check_login, inputs=[username, password], outputs=[login_box,chatbot_user_ui,chatbot_admin_ui, user_state, user_id, user_id1])
    return demo