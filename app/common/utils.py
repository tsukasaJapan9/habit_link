import json
import os
from enum import Enum

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from common.firestore import StudentInfo, load_student_activity_history
from google.cloud.firestore import Client as FirestoreClient
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

SPREAD_SHEET_URL = os.environ["SPREAD_SHEET_URL"]

BUTTON_STYLE_STUDENT = """
    <style>
    /* st.button(type=primary) の見た目を上書き */
    div.stButton > button[kind="primary"] {
        background-color: #EA8760 !important;
        color: white !important;
        border-radius: 40px !important;
        padding: 0.5em 1.2em !important;
        text-align: center !important;
        font-weight: bold;
        border: none;
        display: block;
        margin: 0 auto;
        margin-bottom: -1px !important;
    }

    div.stButton > button[kind="secondary"] {
        background-color: #2C2C2C !important;
        color: white !important;
        border-radius: 40px !important;
        padding: 0.6em 1.5em !important;
        font-weight: bold;
        border: none;
        font-size: 16px;
    }

    .stChatInput {
      margin-bottom: -250px !important;
    }
    </style>
"""

BUTTON_STYLE_TEACHER = """
    <style>
    /* st.button(type=primary) の見た目を上書き */
    div.stButton > button[kind="primary"] {
        background-color: #EA8760 !important;
        color: white !important;
        border-radius: 40px !important;
        padding: 0.5em 1.2em !important;
        text-align: center !important;
        font-weight: bold;
        border: none;
    }

    div.stButton > button[kind="secondary"] {
        background-color: #2C2C2C !important;
        color: white !important;
        border-radius: 40px !important;
        padding: 0.6em 1.5em !important;
        font-weight: bold;
        border: none;
        font-size: 16px;
    }

    .stChatInput {
      margin-bottom: -250px !important;
    }
    
    /* チェックされたラジオボタンの色を黒に */
    input[type="radio"]:checked + div {
        color: black !important;
    }

    /* ラジオの円部分そのものの色 */
    input[type="radio"]:checked {
        accent-color: black !important;
    }

    </style>
"""


class ActivityType(Enum):
  GUITER = (1, "ギター")
  PILATES = (2, "ピラティス")
  WALKING = (3, "ウォーキング")
  JOGGING = (4, "ジョギング")
  CYCLING = (5, "サイクリング")
  SWIMMING = (6, "水泳")
  WORKOUT = (7, "筋トレ")
  YOGA = (8, "ヨガ")

  def __init__(self, value: int, label: str):
    self._value_ = value
    self.label = label

  @classmethod
  def labels(cls) -> list[str]:
    """全ての日本語ラベルをリストで返す"""
    return [member.label for member in cls]


class HabitFrequency(Enum):
  DAILY = (1, "毎日")
  FIVE_PER_WEEK = (2, "週に5回程度")
  THREE_PER_WEEK = (3, "週に3回程度")
  ONCE_PER_WEEK = (4, "週に1回程度")

  def __init__(self, value: int, label: str):
    self._value_ = value
    self.label = label

  @classmethod
  def labels(cls) -> list[str]:
    """全ての日本語ラベルをリストで返す"""
    return [member.label for member in cls]


def create_achievement_goal_str(student_info: StudentInfo) -> str:
  goal = student_info.goal
  goal = goal if goal else "まだ設定されていません"
  return goal


def create_habit_goal_str(student_info: StudentInfo) -> str:
  activity = student_info.activity_type
  timing = student_info.timing
  duration = student_info.duration
  if activity and timing and duration:
    achievement_goal = f"{timing}に{activity}を{duration}分以上やります"
  else:
    achievement_goal = "まだ設定されていません"
  return achievement_goal


def get_summarize_prompt(share_level: str, df: pd.DataFrame) -> str:
  for _, row in df.iterrows():
    if f"summarize_{share_level}" not in row.iloc[0]:
      continue

    prompt = row.iloc[1]
    return prompt

  return ""


def get_system_prompt(phase: int, df: pd.DataFrame) -> str:
  prompt = ""
  for _, row in df.iterrows():
    if "phase" in row.iloc[0] and f"phase{phase}" not in row.iloc[0]:
      continue

    if "summarize_level" in row.iloc[0]:
      continue

    prompt += row.iloc[1]
    prompt += "\n-------------------------\n"

  return prompt


def show_chat_history(firebase_db: FirestoreClient, messages: list[BaseMessage], user_name: str) -> None:
  # ここにfirebase_dbは渡したくないので要リファクタ
  for message in messages:
    content: str = message.content
    if not content:
      continue
    content = content.replace("\\n", "\n")
    if isinstance(message, AIMessage):
      with st.chat_message("Assistant"):
        st.markdown(content)
    elif isinstance(message, HumanMessage):
      if message.name == "calendar":
        show_calendar(firebase_db, user_name)
      else:
        with st.chat_message("User"):
          st.markdown(content)
    elif isinstance(message, ToolMessage):
      # toolは表示しない
      pass
      # with st.chat_message("Tool"):
      #   try:
      #     content = ast.literal_eval(content)
      #     content = [json.loads(c) for c in content]
      #   except (SyntaxError, ValueError):
      #     content = message.content
      #   st.markdown(content)
    else:
      # systemは表示しない
      # with st.chat_message("system"):
      #   st.markdown(content)
      pass


def show_calendar(firebase_db: FirestoreClient, user_name: str) -> None:
  activity_history = load_student_activity_history(firebase_db, user_name)
  activity_history = [data.dump_for_calendar() for data in activity_history]
  events_json = json.dumps(activity_history)

  components.html(
    f"""
  <link href='https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.css' rel='stylesheet' />
  <script src='https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.js'></script>

  <style>
    /* 共通スタイル */
    #calendar {{
      padding: 10px;
      border-radius: 10px;
    }}
    .fc .fc-daygrid-event {{
      border: none;
    }}

    /* ライトモード */
    @media (prefers-color-scheme: light) {{
      # body {{
      #   background-color: #ffffff;
      #   color: #000000;
      # }}
      # #calendar {{
      #   background-color: #f9f9f9;
      #   color: #000000;
      # }}
      # .fc .fc-daygrid-day-number {{
      #   color: #000000;
      # }}
      # .fc .fc-daygrid-event {{
      #   background-color: #1976d2; /* 明るい青系 */
      #   color: #ffffff;
      # }}
      # .fc-toolbar-title, .fc-button {{
      #   color: #000000 !important;
      # }}
      # .fc-button-primary {{
      #   background-color: #00000000;  /* ← より明るく自然な色に修正 */
      #   border: 1px solid #ccc;
      # }}
    }}

    /* ダークモード */
    @media (prefers-color-scheme: dark) {{
      body {{
        background-color: #121212;
        color: #ffffff;
      }}
      #calendar {{
        background-color: #1e1e1e;
        color: #ffffff;
      }}
      .fc .fc-daygrid-day-number {{
        color: #ffffff;
      }}
      .fc .fc-daygrid-event {{
        background-color: #4773ba;
        color: #ffffff;
      }}
      .fc-toolbar-title, .fc-button {{
        color: #ffffff !important;
      }}
      .fc-button-primary {{
        background-color: #333333;
        border: 1px solid #555;
      }}
      .fc-button-primary:not(:disabled).fc-button-active,
      .fc-button-primary:not(:disabled):active {{
        background-color: #009688;
        color: #fff;
      }}
    }}
  </style>

  <div id='calendar'></div>
  <script>
    document.addEventListener('DOMContentLoaded', function() {{
      var calendarEl = document.getElementById('calendar');
      var calendar = new FullCalendar.Calendar(calendarEl, {{
        initialView: 'dayGridMonth',
        locale: 'ja',
        height: 500,
        events: {events_json}
      }});
      calendar.render();
    }});
  </script>
  """,
    height=550,
  )
