import datetime
import pandas as pd
import plotly.graph_objects as go
from IPython.display import HTML
import json

import question

def create_calendar_html(review_data):
    """
    복습 데이터 딕셔너리로부터 HTML 캘린더 시각화를 생성합니다.
    
    인자:
        review_data (dict): 날짜 문자열을 키로 하고 복습 내용 목록을 값으로 가지는 딕셔너리.
                            예시: {'2025-04-12': ['수학 복습', '영어 어휘']}
    
    반환값:
        str: 캘린더 시각화를 나타내는 HTML 문자열
    """
    # Get current month and year
    today = datetime.datetime.now()
    current_month = today.month
    current_year = today.year

    # Get first day of month and number of days in month
    first_day = datetime.datetime(current_year, current_month, 1)
    if current_month == 12:
        last_day = datetime.datetime(current_year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        last_day = datetime.datetime(current_year, current_month + 1, 1) - datetime.timedelta(days=1)

    days_in_month = last_day.day

    # 한국 기준 요일 (0: 월요일, 6: 일요일)로 변환
    # start_day를 월요일을 0으로 설정 (파이썬 기본은 월요일이 0)
    start_day = first_day.weekday()  # 월요일이 0, 일요일이 6

    # Convert date strings to datetime objects
    formatted_data = {}
    for date_str, reviews in review_data.items():
        try:
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
            if date_obj.month == current_month and date_obj.year == current_year:
                formatted_data[date_obj.day] = reviews
        except ValueError:
            continue  # Skip invalid date formats

    # Create HTML
    month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    month_names_kr = ['1월', '2월', '3월', '4월', '5월', '6월',
                      '7월', '8월', '9월', '10월', '11월', '12월']

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            .calendar-container {{
                font-family: 'Arial', sans-serif;
                max-width: 800px;
                margin: 0 auto;
            }}
            .month-header {{
                background-color: #4a86e8;
                color: white;
                padding: 10px;
                text-align: center;
                font-size: 24px;
                border-radius: 5px 5px 0 0;
            }}
            .calendar {{
                display: grid;
                grid-template-columns: repeat(7, 1fr);
                gap: 5px;
                padding: 10px;
                background-color: #f5f5f5;
                border-radius: 0 0 5px 5px;
            }}
            .day-header {{
                text-align: center;
                font-weight: bold;
                padding: 10px;
                background-color: #d9d9d9;
            }}
            .day {{
                min-height: 100px;
                padding: 5px;
                background-color: white;
                border-radius: 5px;
                border: 1px solid #e0e0e0;
                position: relative;
            }}
            .day-number {{
                position: absolute;
                top: 5px;
                right: 5px;
                width: 25px;
                height: 25px;
                background-color: #4a86e8;
                color: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
            }}
            .today {{
                background-color: #fff8e1;
                border: 2px solid #ffb74d;
            }}
            .review-item {{
                background-color: #e3f2fd;
                border-radius: 3px;
                padding: 5px;
                margin-top: 5px;
                font-size: 12px;
                border-left: 3px solid #2196f3;
            }}
            .empty-day {{
                background-color: #f9f9f9;
                opacity: 0.5;
            }}
        </style>
    </head>
    <body>
        <div class="calendar-container">
            <div class="month-header">{month_names_kr[current_month-1]} {current_year}</div>
            <div class="calendar">
                <div class="day-header">월</div>
                <div class="day-header">화</div>
                <div class="day-header">수</div>
                <div class="day-header">목</div>
                <div class="day-header">금</div>
                <div class="day-header">토</div>
                <div class="day-header">일</div>
    """

    # Add empty boxes for days before the start of the month
    for i in range(start_day):
        html += '<div class="day empty-day"></div>'

    # Add days of the month
    for day in range(1, days_in_month + 1):
        is_today = (day == today.day and today.month == current_month and today.year == current_year)
        today_class = " today" if is_today else ""

        html += f'<div class="day{today_class}">'
        html += f'<div class="day-number">{day}</div>'

        # Add review items for this day
        if day in formatted_data:
            for review in formatted_data[day]:
                html += f'<div class="review-item">{review}</div>'

        html += '</div>'

    # Add empty boxes for days after the end of the month
    end_day = (start_day + days_in_month) % 7
    if end_day > 0:
        for i in range(7 - end_day):
            html += '<div class="day empty-day"></div>'

    html += """
            </div>
        </div>
    </body>
    </html>
    """

    return html


def display_calendar(review_data):
    """
    HTML과 Plotly 시각화를 사용하여 캘린더를 표시합니다.

    인자:
        review_data (dict): 날짜 문자열을 키로 하고 복습 내용 목록을 값으로 가지는 딕셔너리.

    반환값:
        tuple: (HTML 캘린더, Plotly 그림 객체)
    """
    html_calendar = create_calendar_html(review_data)
    plotly_calendar = generate_plotly_calendar(review_data)

    return HTML(html_calendar), plotly_calendar

# Example for Gradio interface
def update_calendar_display(review_data_json):
    """
    Gradio 인터페이스에서 캘린더 표시를 업데이트합니다.

    인자:
        review_data_json (str): 복습 데이터의 JSON 문자열

    반환값:
        plotly.graph_objects.Figure: 표시용 Plotly 그림 객체
    """
    try:
        review_data = json.loads(review_data_json)
        fig = generate_plotly_calendar(review_data)
        return fig
    except Exception as e:
        print(f"Error updating calendar: {e}")
        # Return empty figure on error
        return go.Figure()


def check_due_reviews(user_id):
    """
    사용자에게 예정된 복습이 있는지 확인합니다.

    인자:
        user_id (str): 사용자 ID

    반환값:
        str: 예정된 복습에 대한 알림 메시지
    """
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    example_data = question.get_due_review_events(user_id)

    if today in example_data:
        reviews = example_data[today]
        return f"오늘 복습 예정: {', '.join(reviews)}"
    else:
        return "오늘 예정된 복습이 없습니다."

# 이 함수는 Gradio 앱에서 사용
def generate_calendar_overview(user_id):
    """
    주어진 사용자 ID에 대한 캘린더 개요를 생성합니다.

    인자:
        user_id (str): 사용자 ID

    반환값:
        plotly.graph_objects.Figure: 캘린더를 나타내는 Plotly 그림 객체
    """
    # 실제 구현에서는 사용자 ID를 기반으로 데이터베이스에서 리뷰 데이터를 가져와야 함
    # 예시 데이터:
    example_data =  question.get_due_review_events(user_id)
    # 캘린더 시각화 생성 및 반환
    return generate_plotly_calendar(example_data)


def generate_plotly_calendar(review_data):
    """
    복습 데이터가 포함된 캘린더를 나타내는 Plotly 그림 객체를 생성합니다.

    인자:
        review_data (dict): 날짜 문자열을 키로 하고 복습 내용 목록을 값으로 가지는 딕셔너리.

    반환값:
        plotly.graph_objects.Figure: Plotly 그림 객체
    """
    # Get current month data
    today = datetime.datetime.now()
    current_month = today.month
    current_year = today.year

    # 첫 날과 마지막 날 계산
    first_day = datetime.datetime(current_year, current_month, 1)
    if current_month == 12:
        last_day = datetime.datetime(current_year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        last_day = datetime.datetime(current_year, current_month + 1, 1) - datetime.timedelta(days=1)

    # 첫 날의 요일 (0: 월요일, 6: 일요일)
    first_weekday = first_day.weekday()

    # Create calendar data
    calendar_data = []

    # 첫 주에 이전 달의 날짜를 빈 셀로 표시하기 위한 더미 데이터
    for i in range(first_weekday):
        dummy_date = first_day - datetime.timedelta(days=first_weekday-i)
        calendar_data.append({
            'date': dummy_date,
            'day': dummy_date.day,
            'weekday': dummy_date.weekday(),
            'week': 0,  # 첫 주
            'reviews': [],
            'review_count': 0,
            'is_current_month': False  # 현재 달이 아님
        })

    # 이번 달의 모든 날짜 추가
    current_date = first_day
    while current_date.month == current_month:
        date_str = current_date.strftime('%Y-%m-%d')
        reviews = review_data.get(date_str, [])

        # 주차 계산 (첫 주가 0부터 시작)
        # 첫 날의 요일을 고려하여 주차 계산
        week_num = (current_date.day + first_weekday - 1) // 7

        calendar_data.append({
            'date': current_date,
            'day': current_date.day,
            'weekday': current_date.weekday(),
            'week': week_num,
            'reviews': reviews,
            'review_count': len(reviews),
            'is_current_month': True  # 현재 달
        })

        current_date += datetime.timedelta(days=1)

    # Convert to DataFrame
    df = pd.DataFrame(calendar_data)

    # 현재 달만 표시하기 위한 필터링
    current_month_df = df[df['is_current_month'] == True]

    # 빈 셀 포함 DataFrame (캘린더 레이아웃 유지용)
    full_df = df

    # Create Plotly calendar heatmap
    month_names_kr = ['1월', '2월', '3월', '4월', '5월', '6월',
                      '7월', '8월', '9월', '10월', '11월', '12월']
    weekday_names = ['월', '화', '수', '목', '금', '토', '일']

    # 현재 달의 주 수 계산 (0부터 시작하므로 +1)
    max_week = full_df['week'].max() + 1

    # Create hover text
    hover_text = []
    for _, row in full_df.iterrows():
        if row['is_current_month']:
            day_text = f"{row['day']} {month_names_kr[current_month-1]}"
            if row['reviews']:
                reviews_text = '<br>'.join([f"• {review}" for review in row['reviews']])
                day_text += f"<br><br>{reviews_text}"
            hover_text.append(day_text)
        else:
            # 이전 달의 날짜는 빈 호버 텍스트
            hover_text.append("")

    # 데이터 준비 - 현재 달이 아닌 날짜는 리뷰 카운트를 None으로 설정 (빈 셀로 표시)
    z_values = []
    for _, row in full_df.iterrows():
        if row['is_current_month']:
            z_values.append(row['review_count'])
        else:
            z_values.append(None)

    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=full_df['weekday'],
        y=full_df['week'],
        colorscale=[[0, '#f5f5f5'], [0.01, '#d1e5f0'], [1, '#2166ac']],
        showscale=False,
        text=[str(row['day']) if row['is_current_month'] else "" for _, row in full_df.iterrows()],
        hovertext=hover_text,
        hoverinfo='text'
    ))

    # Update layout
    fig.update_layout(
        title=f"{month_names_kr[current_month-1]} {current_year} - 복습 캘린더",
        height=400,
        xaxis=dict(
            tickvals=list(range(7)),
            ticktext=weekday_names,
            side='top'
        ),
        yaxis=dict(
            tickvals=list(range(max_week)),
            ticktext=[f'{i+1}주차' for i in range(max_week)],
            autorange="reversed"
        ),
        margin=dict(l=10, r=10, t=50, b=10)
    )

    # Add day numbers as annotations
    annotations = []
    for _, row in full_df.iterrows():
        if row['is_current_month']:
            annotations.append(dict(
                x=row['weekday'],
                y=row['week'],
                text=str(row['day']),
                showarrow=False,
                font=dict(
                    color='black',
                    size=12
                )
            ))

    fig.update_layout(annotations=annotations)

    return fig