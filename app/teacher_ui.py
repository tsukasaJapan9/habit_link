import ast
import copy
import json
from collections import deque

import firebase_admin
import pandas as pd
import requests
import streamlit as st
from common.firestore import (
  SHARE_LEVEL,
  chat_history_to_str,
  get_student_list,
  load_student_activity_history,
  load_student_info,
  load_teacher_info,
  save_teacher_info,
  str_to_chat_history,
)
from common.params import DEBUG_MESSAGE_SIZE, INF_SERVER_URL, MAX_HISTORY_NUM, SEND_MSG_SIZE, TEACHER_PROMPT_GID
from common.utils import (
  BUTTON_STYLE_TEACHER,
  SPREAD_SHEET_URL,
  create_achievement_goal_str,
  create_habit_goal_str,
  get_system_prompt,
  show_chat_history,
)
from firebase_admin import firestore
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages.base import messages_to_dict
from langchain_core.messages.utils import messages_from_dict

# TODO: loggerを導入する
DEBUG = False

st.set_page_config(page_title="HabitLink for Teacher")


# firebase
if not firebase_admin._apps:
  firebase_app = firebase_admin.initialize_app(options={"projectId": "habit-agent"})
firebase_db = firestore.client()


st.markdown(
  BUTTON_STYLE_TEACHER,
  unsafe_allow_html=True,
)


def create_chat_summary(chat_history: list[BaseMessage]) -> str:
  print("---------- create summary ----------")
  chat_hisutory_only_human = [message.content for message in chat_history if isinstance(message, HumanMessage)]
  system_prompt = """
  ### タスク
  あなたはピラティスのインストラクターです。
  「ピラティスのインストラクターのメモ」を参照し、
  生徒に伝えるべきことがあれば重要度が高い順番に3つまで
  抽出して一項目100文字以内でまとめてください。

  ### ルール
  - インストラクターが生徒に話しかけるようなやさしい口調で出力してください。
  - 以下のフォーマットに従って項目のみ出力してください。項目以外は絶対出力しないでください。
  - 項目の前の文章は不要です。
  ```
  1. xxxx
  2. xxxx
  3. xxxx
  ```
  """
  system_message = SystemMessage(content=system_prompt)

  user_prompt = f"""
  ### ピラティスのインストラクターのメモ
  {chat_hisutory_only_human}
  """
  user_message = HumanMessage(content=user_prompt)

  json_input_data = messages_to_dict([system_message, user_message])
  json_str = json.dumps(json_input_data, indent=2)
  try:
    # 推論
    response = requests.post(INF_SERVER_URL + "/infer", json={"message": json_str})
    json_data = response.json()
    json_data = json.loads(json_data["response"])
  except json.decoder.JSONDecodeError:
    print("failed to parse json")
    json_data = json_input_data
  try:
    recevied_msgs = messages_from_dict(json_data)
  except Exception as e:
    print(f"エラーが発生しました: {e}")
    return ""
  return recevied_msgs[-1].content


@st.dialog("生徒の重点項目設定")
def set_instruction(teacher_name: str, user_name: str) -> None:
  # UIのデフォルト値を設定するためJSTで時刻を取得
  instruction = st.text_area("重点項目を具体的に書いてください", placeholder="例: 首、背中を重点的に", height=120)

  # 記録ボタン
  if st.button("設定する", key="set_instruction_button") and instruction:
    st.session_state.instruction = instruction
    save_teacher_info(
      firebase_db,
      teacher_name,
      user_name,
      chat_history_to_str(st.session_state.chat_history),
      st.session_state.chat_summary,
      st.session_state.instruction,
    )
    st.success("設定しました。")
    st.rerun()


def main() -> None:
  # =======================================
  # ページタイトルの設定など
  # =======================================
  st.title("HabitLink for Teacher")

  # =======================================
  # 利用可能なツールの取得
  # =======================================
  response = requests.get(INF_SERVER_URL + "/tools")
  json_data = response.json()
  json_data = json.loads(json_data["tools"])

  # =======================================
  # 先生の名前の取得
  # =======================================
  params = st.query_params
  teacher_name = params.get("teacher_name", "")
  teacher_name = teacher_name.strip('"')

  if not teacher_name:
    st.error("URLに先生名を設定してください(?teacher_name=teacher name)。")
    return

  # =======================================
  # サイドバー
  # =======================================
  # 生徒の選択
  # TODO: user_nameはstudent nameにrenameする
  st.sidebar.header("生徒")
  user_names = get_student_list(firebase_db)
  user_name = st.sidebar.radio("状況を確認する生徒を選んでください", tuple(user_names))
  if "student_info" not in st.session_state or st.session_state.student_info.user_name != user_name:
    chat_history, chat_summary, instruction = load_teacher_info(firebase_db, teacher_name, user_name)
    if chat_history:
      st.session_state.chat_history = str_to_chat_history(chat_history)
    else:
      st.session_state.chat_history = deque(maxlen=MAX_HISTORY_NUM)

    st.session_state.chat_summary = chat_summary
    st.session_state.instruction = instruction

  st.session_state.student_info = load_student_info(firebase_db, user_name)
  st.session_state.activity_history = load_student_activity_history(firebase_db, user_name)
  print(f"Loaded student name: {st.session_state.student_info.user_name}")

  st.sidebar.header(f"{user_name}さんの実施実績")
  if st.sidebar.button("実施実績を確認する", type="primary"):
    st.session_state.temporary_message = f"{user_name}さんのカレンダーを表示"

  st.sidebar.header(f"{user_name}さんの重点取り組み")
  instruction_str = st.session_state.instruction if st.session_state.instruction else "まだ設定されていません"
  st.sidebar.write(instruction_str)

  if st.sidebar.button("設定する"):
    set_instruction(teacher_name, user_name)

  st.sidebar.header(f"{user_name}さんの様子")
  if st.session_state.student_info.chat_summary:
    st.sidebar.write(st.session_state.student_info.chat_summary)
  else:
    st.sidebar.write("まだ作成されていません")

  st.sidebar.header(f"{user_name}さんの習慣プラン")

  st.sidebar.subheader("習慣目標")
  habit_goal = create_habit_goal_str(st.session_state.student_info)
  st.sidebar.write(habit_goal)

  st.sidebar.subheader("達成目標")
  achivement_goal = create_achievement_goal_str(st.session_state.student_info)
  st.sidebar.write(achivement_goal)

  st.sidebar.markdown("---")

  st.sidebar.header(f"{user_name}さんからの情報共有範囲")
  share_level = st.session_state.student_info.share_level
  if share_level:
    st.sidebar.write(SHARE_LEVEL[share_level]["label"])
  else:
    st.sidebar.write("まだ設定されていません")

  # st.sidebar.header("Tools")
  # for name in json_data.keys():
  #   st.sidebar.write(f"{name}")

  # =======================================
  # session stateの初期化
  # =======================================
  if "chat_history" not in st.session_state:
    st.session_state.chat_history = deque(maxlen=MAX_HISTORY_NUM)

  if "chat_summary" not in st.session_state:
    st.session_state.chat_summary = ""

  if "activity_history" not in st.session_state:
    st.session_state.activity_history = []

  if "instruction" not in st.session_state:
    st.session_state.instruction = ""

  if "temporary_message" not in st.session_state:
    st.session_state.temporary_message = ""

  if "show_calendar" not in st.session_state:
    st.session_state.show_calendar = False

  if "user_input" not in st.session_state:
    st.session_state.user_input = ""

  if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = ""

  st.header(f"{teacher_name}先生、こんにちわ!")
  st.warning("注意: 使い終わったら必ずブラウザや本タブを閉じてください")

  # 生徒とエージェント間で行われた会話履歴をロード
  if st.session_state.student_info.chat_summary:
    student_agent_chat_summary = st.session_state.student_info.chat_summary
  else:
    student_agent_chat_summary = "まだサマリは作成されていません"

  url = f"{SPREAD_SHEET_URL}&gid={TEACHER_PROMPT_GID}"
  spreadsheet_df = pd.read_csv(url, header=None)

  phase = 2 if st.session_state.student_info.goal else 1
  if phase == 1:
    goal = "まだ設定されていません"
  else:
    goal = create_achievement_goal_str(st.session_state.student_info)
    goal += "\n"
    goal += create_habit_goal_str(st.session_state.student_info)
  system_prompt = get_system_prompt(phase=phase, df=spreadsheet_df)
  activity_history_for_prompt = [
    history.start_time.strftime("%Y-%m-%d") for history in st.session_state.activity_history
  ]
  activity_history_for_prompt = sorted(list(set(activity_history_for_prompt)), reverse=True)
  activity_history_for_prompt = "\n".join(activity_history_for_prompt)
  value = {
    "user_name": user_name,
    "habit_goal": goal,
    "activity_history": activity_history_for_prompt,
    "student_agent_chat": student_agent_chat_summary,
  }
  system_prompt = system_prompt.format(**value)
  st.session_state.system_prompt = system_prompt

  # =======================================
  # チャット履歴の描画
  # =======================================
  # TODO: chat_historyを適宜DBに保存して読み出す
  show_chat_history(firebase_db, st.session_state.chat_history, user_name)

  # =======================================
  # ユーザの入力を受け付けて推論する
  # =======================================
  chat_input = st.chat_input("何でも入力してね")
  temporary_message = None
  calendar_message = None
  if st.session_state.temporary_message:
    temporary_message = st.session_state.temporary_message
    st.session_state.temporary_message = ""
    calendar_message = HumanMessage(content="test", name="calendar")

  user_input = ""
  if chat_input:
    user_input = chat_input
  elif temporary_message:
    user_input = temporary_message

  if user_input:
    st.session_state.chat_history.append(HumanMessage(content=user_input))
  if calendar_message:
    st.session_state.chat_history.append(calendar_message)

  # カレンダーの描画などを行うとrerunが走る可能性があるため、事前にsession_stateに保存する
  st.session_state.user_input = user_input

  # カレンダーの描画等
  if user_input:
    show_chat_history(firebase_db, [HumanMessage(content=user_input)], user_name)
  if calendar_message:
    show_chat_history(firebase_db, [calendar_message], user_name)
    st.rerun()

  if st.session_state.user_input:
    user_input = st.session_state.user_input
    st.session_state.user_input = ""

  if user_input:
    with st.spinner("AI agent is typing..."):
      # 会話履歴 + ユーザの入力をjsonにしてAPIで推論サーバにpost
      print("=================================")

      # すべての履歴を送ると推論に時間がかかるので直近の数個を送る
      # chat_historyにSystemMessageは無いため先頭に付与する
      chat_history = copy.copy(list(st.session_state.chat_history)[-SEND_MSG_SIZE:])
      chat_history.insert(0, SystemMessage(content=f"{st.session_state.system_prompt}", id=0))
      sent_message_len = len(chat_history)

      if DEBUG:
        print("---------- [UI]: send data to infer server ----------")
        for message in chat_history:
          print(
            f"{message.__class__.__name__}(name: {message.name}, id: {message.id}): {message.content[:DEBUG_MESSAGE_SIZE]}"
          )

      json_input_data = messages_to_dict(chat_history)
      json_str = json.dumps(json_input_data, indent=2)
      try:
        # 推論
        response = requests.post(INF_SERVER_URL + "/infer", json={"message": json_str})

        json_data = response.json()
        json_data = json.loads(json_data["response"])
      except json.decoder.JSONDecodeError:
        print("failed to parse json")
        json_data = json_input_data

      # 推論サーバからデータがjsonで来るのでlangchainのオブジェクトに変換
      try:
        recevied_msgs = messages_from_dict(json_data)
      except Exception as e:
        print(f"エラーが発生しました: {e}")
        recevied_msgs = []
      if DEBUG:
        print("---------- [UI]: receved data from infer server ----------")

      # 送信したメッセージに対して受信で増えた分だけを履歴に追加
      chat_history = copy.copy(st.session_state.chat_history)
      for message in recevied_msgs[sent_message_len:]:
        chat_history.append(message)
      st.session_state.chat_history = chat_history

    # チャットサマリの作成
    chat_history_for_summary = copy.deepcopy(st.session_state.chat_history)
    summary = create_chat_summary(chat_history_for_summary)
    st.session_state.chat_summary = summary

    # 推論サーバが追加で返してきた分のみ描画する
    show_chat_history(firebase_db, recevied_msgs[sent_message_len:], user_name)

    # chat情報の保存
    save_teacher_info(
      firebase_db,
      teacher_name,
      user_name,
      chat_history_to_str(st.session_state.chat_history),
      st.session_state.chat_summary,
      st.session_state.instruction,
    )

    # for debug
    if DEBUG:
      for message in recevied_msgs:
        if isinstance(message, ToolMessage):
          try:
            contents = ast.literal_eval(message.content)
            contents = [json.loads(content) for content in contents]
          except (SyntaxError, ValueError):
            contents: str = message.content
        else:
          contents: str = message.content
        print(
          f"{message.__class__.__name__}(name: {message.name}, id: {message.id}): {message.content[:DEBUG_MESSAGE_SIZE]}"
        )


if __name__ == "__main__":
  main()
