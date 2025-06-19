import ast
import copy
import json
from datetime import datetime

import firebase_admin
import pandas as pd
import requests
import streamlit as st
from common.firestore import (
  SHARE_LEVEL,
  ActivityData,
  StudentInfo,
  load_student_activity_history,
  load_student_info,
  load_teacher_info,
  save_student_activity_data,
  save_student_info,
  save_teacher_info,
)
from common.params import DEBUG_MESSAGE_SIZE, INF_SERVER_URL, JST, SEND_MSG_SIZE, STUDENT_PROMPT_GID
from common.utils import (
  BUTTON_STYLE_STUDENT,
  SPREAD_SHEET_URL,
  ActivityType,
  HabitFrequency,
  create_achievement_goal_str,
  create_habit_goal_str,
  get_summarize_prompt,
  get_system_prompt,
  show_chat_history,
)
from firebase_admin import firestore
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages.base import messages_to_dict
from langchain_core.messages.utils import messages_from_dict
from pyparsing import deque

st.set_page_config(page_title="HabitLink for Student")


# TODO: loggerを導入する
DEBUG = False

# firebase
if not firebase_admin._apps:
  firebase_app = firebase_admin.initialize_app(options={"projectId": "habit-agent"})
firebase_db = firestore.client()


st.markdown(
  BUTTON_STYLE_STUDENT,
  unsafe_allow_html=True,
)


def create_chat_summary(chat_history: deque[BaseMessage], df: pd.DataFrame, student_info: StudentInfo) -> str:
  print("---------- create summary ----------")
  chat_history_only_human = [
    message.content for message in chat_history if isinstance(message, HumanMessage) and message.name != "calendar"
  ]
  system_prompt = get_summarize_prompt(student_info.share_level, df)
  system_message = SystemMessage(content=system_prompt)
  user_prompt = f"""
  ### 生徒の会話
  {chat_history_only_human}
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


def start_activity(user_name: str, instruction_from_teacher: str):
  now_jst = datetime.now(JST)
  activity_type = ActivityType.PILATES.label

  activity_data = ActivityData(
    start_time=now_jst,
    duration=0,
    activity_type=activity_type,
    created_at=now_jst,
  )
  save_student_activity_data(firebase_db, user_name, activity_data)
  if instruction_from_teacher:
    msg = f"ピラティスを始めます。先生からの指示である「{instruction_from_teacher}」に関する動画を探してください。"
  else:
    msg = "ピラティスを始めます。先生からの指示は無いので、「全身の運動」に関する動画を探してください。"
  st.session_state.temporary_message = msg
  st.rerun()


@st.dialog("習慣プラン設定")
def set_goal(user_name: str):
  st.subheader("ピラティスを習慣化するための目標")

  # UIのデフォルト値を設定するためJSTで時刻を取得
  activity_type = ActivityType.PILATES.label
  habit_freq = HabitFrequency.DAILY.label
  timing = st.text_area("タイミング　＊日常の行動の前後にするのがコツ", placeholder="例: 朝食の後", height=68)
  time_range = [1, 3, 5, 10, 15, 30, 45, 60]
  time_labels = [f"{i}分以上" for i in time_range]
  selected_label = st.selectbox("時間　＊無理の無い最低目標にするのがコツ", time_labels)
  duration = int(selected_label.replace("分以上", ""))
  goal = st.text_area("ピラティスを通して実現したい目標を設定しよう", height=68)

  col1, col2 = st.columns(2)

  # 記録ボタン
  with col1:
    if st.button("目標を設定する") and activity_type and habit_freq and duration and timing and goal:
      st.session_state.student_info.activity_type = activity_type
      st.session_state.student_info.habit_freq = habit_freq
      st.session_state.student_info.duration = duration
      st.session_state.student_info.timing = timing
      st.session_state.student_info.goal = goal
      save_student_info(
        firebase_db=firebase_db,
        student_info=st.session_state.student_info,
      )
      st.success("設定しました。")
      st.session_state.temporary_message = (
        f"私の目標は{goal}。そのために{activity_type}を{timing}に{duration}分以上やります。"
      )
      st.rerun()

  with col2:
    if st.button("目標をリセット", type="tertiary"):
      st.session_state.student_info.activity_type = ActivityType.PILATES.label
      st.session_state.student_info.habit_freq = ""
      st.session_state.student_info.duration = 0
      st.session_state.student_info.timing = ""
      st.session_state.student_info.goal = ""
      st.session_state.student_info.chat_history = deque(maxlen=SEND_MSG_SIZE)
      st.session_state.student_info.chat_summary = ""

      save_student_info(
        firebase_db=firebase_db,
        student_info=st.session_state.student_info,
      )

      save_teacher_info(
        firebase_db=firebase_db,
        teacher_name=st.session_state.teacher_name,
        student_name=user_name,
        chat_history="",
        chat_summary="",
        instruction="",
      )

      st.success("リセットしました。")
      st.session_state.temporary_message = """
      新しい習慣計画を立てるために目標をリセットしました。
      """
      st.rerun()


@st.dialog("目標をリセットしてもいいですか？")
def reset_goal(user_name: str):
  st.subheader("目標をリセットするとチャット履歴もクリアされます")
  # 記録ボタン
  if st.button("はい"):
    st.session_state.student_info.activity_type = ActivityType.PILATES.label
    st.session_state.student_info.habit_freq = ""
    st.session_state.student_info.duration = 0
    st.session_state.student_info.timing = ""
    st.session_state.student_info.goal = ""
    st.session_state.student_info.chat_history = deque(maxlen=SEND_MSG_SIZE)
    st.session_state.student_info.chat_summary = ""
    save_student_info(
      firebase_db=firebase_db,
      student_info=st.session_state.student_info,
    )
    st.success("リセットしました。")
    st.session_state.temporary_message = """
    新しい習慣計画を立てるために目標をリセットしました。
    """
    st.rerun()


@st.dialog("情報共有範囲の選択")
def set_share_level(user_name: str):
  st.write(
    """
AIに話した情報のうち、どこまで共有するか選べます。
多く共有するほど、よりあなたに合わせた提案が可能です。
  """
  )

  # selectbox
  labels = [v["label"] for v in SHARE_LEVEL.values()]
  label_to_key = {v["label"]: k for k, v in SHARE_LEVEL.items()}
  selected_label = st.selectbox("共有範囲を選んでください：", options=labels)
  selected_key = label_to_key[selected_label]

  # 表示エリア
  for key, value in SHARE_LEVEL.items():
    if key == selected_key:
      st.markdown(
        f"""
  <div style="background-color:#e6f7ff;padding:1em;border-left:5px solid #1890ff;border-radius:6px;">
  <b>{value["label"]}</b>

  {value["description"]}
  </div>
  """,
        unsafe_allow_html=True,
      )
    else:
      st.markdown(
        f"""
  <div style="padding:1em;border-bottom:1px solid #ddd;">
  <b>{value["label"]}</b>

  {value["description"]}
  </div>
  """,
        unsafe_allow_html=True,
      )

  st.markdown("")

  # 記録ボタン
  if st.button("設定する") and selected_key:
    st.session_state.student_info.share_level = selected_key
    save_student_info(
      firebase_db=firebase_db,
      student_info=st.session_state.student_info,
    )
    st.success("設定しました。")
    st.rerun()


def main() -> None:
  # =======================================
  # ページタイトルの設定など
  # =======================================
  st.title("HabitLink for Student")

  # =======================================
  # 利用可能なツールの取得
  # =======================================
  response = requests.get(INF_SERVER_URL + "/tools")
  json_data = response.json()
  json_data = json.loads(json_data["tools"])

  # =======================================
  # サイドバー
  # =======================================
  # ユーザ名と先生名の取得
  params = st.query_params
  # TODO: user nameはstudent_nameにrenameする
  user_name = params.get("user_name", "")
  user_name = user_name.strip('"')

  teacher_name = params.get("teacher_name", "")
  teacher_name = teacher_name.strip('"')

  if not user_name or not teacher_name:
    st.error("URLに生徒名と先生名を設定してください(?user_name=your name&teacher_name=your teacher name)。")
    return

  if "student_info" not in st.session_state or st.session_state.student_info.user_name != user_name:
    # ユーザ名が変わったら目標をロードしなおしてチャット履歴もクリア
    st.session_state.student_info = load_student_info(firebase_db, user_name)
    print(f"Loaded student name: {st.session_state.student_info.user_name}")

    # 先生とエージェント間で行われた会話履歴と生徒への指示をロード
  _, teacher_agent_chat_summary, instruction_from_teacher = load_teacher_info(
    firebase_db, teacher_name, st.session_state.student_info.user_name
  )
  st.session_state.instruction_from_teacher = instruction_from_teacher
  st.session_state.teacher_agent_chat_summary = teacher_agent_chat_summary

  # if st.button("習慣スタート", disabled=not bool(st.session_state.student_info.goal), type="primary"):
  #   start_activity(st.session_state.student_info.user_name, st.session_state.instruction_from_teacher)

  # query_params = st.query_params

  # if "trigger" in st.query_params:
  #   start_activity(st.session_state.student_info.user_name, st.session_state.instruction_from_teacher)
  #   # パラメータを削除（リロード時に再発火しないように）
  #   st.query_params.clear()

  # st.markdown(
  #   """
  #     <style>
  #     .fixed-button {
  #         position: fixed;
  #         bottom: 20px;
  #         right: 20px;
  #         z-index: 9999;
  #         background-color: #4CAF50;
  #         color: white;
  #         padding: 10px 20px;
  #         border-radius: 10px;
  #         text-align: center;
  #     }
  #     </style>
  #     <div class="fixed-button" onclick="start_activity(st.session_state.student_info.user_name, st.session_state.instruction_from_teacher)">実行</div>
  # """,
  #   unsafe_allow_html=True,
  # )

  st.sidebar.header("あなたの習慣プラン")

  st.sidebar.subheader("習慣目標")
  habit_goal = create_habit_goal_str(st.session_state.student_info)
  st.sidebar.write(habit_goal)

  st.sidebar.subheader("達成目標")
  create_achievement_goal = create_achievement_goal_str(st.session_state.student_info)
  st.sidebar.write(create_achievement_goal)

  if st.sidebar.button("プラン設定"):
    set_goal(st.session_state.student_info.user_name)

  st.sidebar.header("先生が設定した重点取り組み")
  if st.session_state.instruction_from_teacher:
    st.sidebar.write(st.session_state.instruction_from_teacher)
  else:
    st.sidebar.write("設定されていません")

  st.sidebar.header("先生からの伝言")
  if st.session_state.teacher_agent_chat_summary:
    st.sidebar.write(st.session_state.teacher_agent_chat_summary)
  else:
    st.sidebar.write("伝言はありません")

  st.sidebar.markdown("---")

  st.sidebar.header("先生への情報共有範囲")
  share_level = st.session_state.student_info.share_level
  if share_level:
    st.sidebar.write(SHARE_LEVEL[share_level]["label"])
  else:
    st.sidebar.write("まだ設定されていません")

  if st.sidebar.button("情報共有の範囲の設定"):
    set_share_level(user_name)

  # st.sidebar.subheader("その他")

  # if st.sidebar.button("目標をリセット"):
  #   reset_goal(st.session_state.student_info.user_name)

  # st.sidebar.header("Tools")
  # for name in json_data.keys():
  #   st.sidebar.write(f"{name}")

  # =======================================
  # session stateの初期化
  # =======================================
  if "activity_history" not in st.session_state:
    st.session_state.activity_history = []

  if "temporary_message" not in st.session_state:
    st.session_state.temporary_message = ""

  if "show_calendar" not in st.session_state:
    st.session_state.show_calendar = False

  if "user_input" not in st.session_state:
    st.session_state.user_input = ""

  if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = ""

  st.session_state.teacher_name = teacher_name

  st.header(f"こんにちは {st.session_state.student_info.user_name}さん!")
  st.warning("注意: 使い終わったら必ずブラウザや本タブを閉じてください")

  # =======================================
  # DBからユーザのデータやプロンプトをロード
  # =======================================
  url = f"{SPREAD_SHEET_URL}&gid={STUDENT_PROMPT_GID}"
  spreadsheet_df = pd.read_csv(url, header=None)

  st.session_state.activity_history = load_student_activity_history(
    firebase_db, st.session_state.student_info.user_name
  )

  activity_history_for_prompt = [
    history.start_time.strftime("%Y-%m-%d") for history in st.session_state.activity_history
  ]
  activity_history_for_prompt = sorted(list(set(activity_history_for_prompt)), reverse=True)
  activity_history_for_prompt = "\n".join(activity_history_for_prompt)
  phase = 2 if st.session_state.student_info.goal else 1
  if phase == 1:
    goal = "まだ設定されていません"
  else:
    goal = create_achievement_goal_str(st.session_state.student_info)
    goal += ","
    goal += create_habit_goal_str(st.session_state.student_info)

  system_prompt = get_system_prompt(phase=phase, df=spreadsheet_df)
  value = {
    "user_name": st.session_state.student_info.user_name,
    "habit_goal": goal,
    "activity_history": activity_history_for_prompt,
    "teacher_agent_chat": teacher_agent_chat_summary,
  }
  system_prompt = system_prompt.format(**value)
  st.session_state.system_prompt = system_prompt

  # =======================================
  # チャット履歴の描画
  # =======================================
  show_chat_history(
    firebase_db,
    st.session_state.student_info.chat_history,
    st.session_state.student_info.user_name,
  )

  # =======================================
  # ユーザの入力を受け付けて推論する
  # =======================================
  chat_input = st.chat_input("何でも入力してね")
  temporary_message = None
  calendar_message = None
  if st.session_state.temporary_message:
    temporary_message = st.session_state.temporary_message
    st.session_state.temporary_message = ""

    # TODO:
    # - firestoreのデータを読み取りデータをchat_historyに入れる
    calendar_message = HumanMessage(content="test", name="calendar")

  user_input = ""
  if chat_input:
    user_input = chat_input
  elif temporary_message:
    user_input = temporary_message

  if user_input:
    st.session_state.student_info.chat_history.append(HumanMessage(content=user_input))
  if calendar_message:
    st.session_state.student_info.chat_history.append(calendar_message)

  # カレンダーの描画などを行うとrerunが走る可能性があるため、事前にsession_stateに保存する
  st.session_state.user_input = user_input

  # カレンダーの描画等
  if user_input:
    show_chat_history(
      firebase_db,
      [HumanMessage(content=user_input)],
      st.session_state.student_info.user_name,
    )
  if calendar_message:
    show_chat_history(
      firebase_db,
      [calendar_message],
      st.session_state.student_info.user_name,
    )

  if st.session_state.user_input:
    user_input = st.session_state.user_input
    st.session_state.user_input = ""

  if user_input:
    with st.spinner("AI agent is typing..."):
      # 会話履歴 + ユーザの入力をjsonにしてAPIで推論サーバにpost
      print("=================================")

      # すべての履歴を送ると推論に時間がかかるので直近の数個を送る
      # chat_historyにSystemMessageは無いため先頭に付与する
      chat_history = copy.copy(list(st.session_state.student_info.chat_history)[-SEND_MSG_SIZE:])
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
      # 送信したメッセージに対して受信で増えた分だけを履歴に追加
      chat_history = copy.copy(st.session_state.student_info.chat_history)
      for message in recevied_msgs[sent_message_len:]:
        chat_history.append(message)
      st.session_state.student_info.chat_history = chat_history

    # チャットサマリの作成
    chat_history_for_summary = copy.deepcopy(st.session_state.student_info.chat_history)
    summary = create_chat_summary(
      chat_history_for_summary, df=spreadsheet_df, student_info=st.session_state.student_info
    )
    st.session_state.student_info.chat_summary = summary

    # 推論サーバが追加で返してきた分のみ描画する
    show_chat_history(firebase_db, recevied_msgs[sent_message_len:], user_name)
    # chat historyの保存
    save_student_info(firebase_db, st.session_state.student_info)
    # for debug
    if DEBUG:
      print("---------- [UI]: receved data from infer server ----------")
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

  if st.button("習慣スタート", disabled=not bool(st.session_state.student_info.goal), type="primary"):
    start_activity(st.session_state.student_info.user_name, st.session_state.instruction_from_teacher)


if __name__ == "__main__":
  main()
