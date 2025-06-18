import json
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Deque

from common.params import JST, MAX_HISTORY_NUM
from firebase_admin import firestore
from google.api_core.exceptions import GoogleAPICallError, PermissionDenied
from google.cloud.firestore import Client as FirestoreClient
from google.cloud.firestore_v1 import FieldFilter
from langchain_core.messages import BaseMessage
from langchain_core.messages.base import messages_to_dict
from langchain_core.messages.utils import messages_from_dict
from pydantic import BaseModel, Field


def chat_history_to_str(messages: list[BaseMessage]) -> str:
  # AIMessageとHumanMessageのみstrに変換する
  # messages = [message for message in messages if isinstance(message, AIMessage) or isinstance(message, HumanMessage)]
  messages_dict = messages_to_dict(messages)
  return json.dumps(messages_dict, ensure_ascii=False)


def str_to_chat_history(chat_str: str) -> list[BaseMessage]:
  loaded_dict = json.loads(chat_str)
  return deque(messages_from_dict(loaded_dict), maxlen=MAX_HISTORY_NUM)


def create_timing_str(
  activity_type: str,
  timing: str,
  duration: int,
) -> str:
  if activity_type and timing and duration > 0:
    goal_str = f"{activity_type}を{timing}に{duration}分やります！"
  else:
    goal_str = ""
  return goal_str


# 先生用
# 生徒のリストを取得する
def get_student_list(firebase_db: FirestoreClient) -> list[str]:
  users_ref = firebase_db.collection("users")
  docs = users_ref.stream()
  user_names = [doc.id for doc in docs]

  return user_names


SHARE_LEVEL = {
  "level2": {
    "label": "幅広く共有する（生活・健康・こころまで）※推奨",
    "description": "生活習慣や健康状態、気分などをふまえた、よりパーソナルなアドバイスを受けられます。",
  },
  "level1": {
    "label": "必要最低限だけ共有する（目標・運動について）",
    "description": "運動の目標や希望など、基本的な情報にあわせたサポートが受けられます。",
  },
}


class StudentInfo(BaseModel):
  user_name: str
  activity_type: str
  habit_freq: str
  duration: int
  timing: str
  goal: str
  share_level: str
  chat_history: Deque[BaseMessage] = Field(default_factory=lambda: deque(maxlen=MAX_HISTORY_NUM))
  chat_summary: str
  created_at: datetime
  updated_at: datetime

  def dump(self) -> dict[str, Any]:
    return {
      "user_name": self.user_name,
      "activity_type": self.activity_type,
      "habit_freq": self.habit_freq,
      "duration": self.duration,
      "timing": self.timing,
      "goal": self.goal,
      "share_level": self.share_level,
      "chat_history": chat_history_to_str(self.chat_history),
      "chat_summary": self.chat_summary,
      # 時刻はunix time(UTC)で保存
      "created_at": self.created_at.timestamp(),
      "updated_at": self.updated_at.timestamp(),
    }

  @classmethod
  def from_dict(cls, user_name: str, data: dict[str, Any]) -> "StudentInfo":
    return cls(
      user_name=user_name,
      activity_type=data.get("activity_type", ""),
      habit_freq=data.get("habit_freq", ""),
      duration=data.get("duration", 0),
      timing=data.get("timing", ""),
      goal=data.get("goal", ""),
      share_level=data.get("share_level", "level1"),
      chat_history=str_to_chat_history(data.get("chat_history", "")),
      chat_summary=data.get("chat_summary", ""),
      created_at=datetime.fromtimestamp(data.get("created_at", 0), tz=JST),
      updated_at=datetime.fromtimestamp(data.get("updated_at", 0), tz=JST),
    )


class ActivityData(BaseModel):
  start_time: datetime
  duration: int
  activity_type: str
  created_at: datetime

  def dump(self) -> dict[str, Any]:
    # 時刻はunix time(UTC)で保存
    return {
      "start_time": self.start_time.timestamp(),
      "end_time": self.duration,
      "activity_type": self.activity_type,
      "created_at": self.created_at.timestamp(),
    }

  def dump_for_calendar(self) -> dict[str, Any]:
    return {
      "date": self.start_time.strftime("%Y-%m-%d"),
      "title": self.activity_type,
    }

  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> "ActivityData":
    return cls(
      start_time=datetime.fromtimestamp(data.get("start_time", 0), tz=JST),
      duration=data.get("duration", 0),
      activity_type=data.get("activity_type", ""),
      created_at=datetime.fromtimestamp(data.get("created_at", 0), tz=JST),
    )


# 生徒用
# 実施したアクティビティ状況を保存する
def save_student_activity_data(
  firebase_db: FirestoreClient,
  user_name: str,
  activity_data: ActivityData,
) -> dict[str, Any]:
  try:
    firebase_db.collection("users").document(user_name).collection("activity_logs").add(activity_data.dump())
    print(f"Data of activity successfully added({user_name}): {activity_data}")
  except PermissionDenied as e:
    print(f"Permission error: {e}")
  except GoogleAPICallError as e:
    print(f"Firestore API error: {e}")
  except Exception as e:
    print(f"Unexpected error: {e}")
  return activity_data


# 先生と生徒用
# get_activity_historyを通して、生徒のアクティビティの実施履歴を取得する
def load_student_activity_history(firebase_db: FirestoreClient, user_name: str, days: int = 30) -> list[Any]:
  # DBにはUTCで保存されている
  now_utc = datetime.now(tz=timezone.utc)
  one_month_ago = now_utc - timedelta(days=days)
  month_ago_ts = one_month_ago.timestamp()

  logs_ref = firebase_db.collection("users").document(user_name).collection("activity_logs")
  query = logs_ref.where(filter=FieldFilter("start_time", ">=", month_ago_ts)).order_by(
    "start_time", direction=firestore.Query.DESCENDING
  )
  docs = query.stream()

  activity_history = []
  for doc in docs:
    doc = doc.to_dict()
    activity_history.append(ActivityData.from_dict(doc))
  return activity_history


# 生徒用
# 生徒の習慣化目標、チャット履歴などを保存する
# TODO: 共有レベルを保存するように改造する
# TODO: 任意ゴールも保存できるようにする
def save_student_info(firebase_db: FirestoreClient, student_info: StudentInfo) -> bool:
  try:
    firebase_db.collection("users").document(student_info.user_name).set(student_info.dump())
    print(f"Data of student info successfully added({student_info.user_name})")
  except PermissionDenied as e:
    print(f"Permission error: {e}")
    return False
  except GoogleAPICallError as e:
    print(f"Firestore API error: {e}")
    return False
  except Exception as e:
    print(f"Unexpected error: {e}")
    return False
  return True


# 先生と生徒用
# 生徒が設定した習慣化目標を取得する
def load_student_info(firebase_db: FirestoreClient, user_name: str) -> StudentInfo:
  ref = firebase_db.collection("users").document(user_name)
  doc = ref.get()
  if doc.exists:
    user_data = doc.to_dict()
    return StudentInfo.from_dict(user_name, user_data)
  return StudentInfo(
    user_name=user_name,
    activity_type="",
    habit_freq="",
    duration=0,
    timing="",
    goal="",
    share_level="level1",
    chat_history=deque(maxlen=MAX_HISTORY_NUM),
    chat_summary="",
    created_at=datetime.now(tz=JST),
    updated_at=datetime.now(tz=JST),
  )


# 先生用
# 先生とAI間のチャット履歴を保存する
def save_teacher_info(
  firebase_db: FirestoreClient,
  teacher_name: str,
  student_name: str,
  chat_history: str,
  chat_summary: str,
  instruction: str,
) -> None:
  try:
    doc_ref = firebase_db.collection("teachers").document(teacher_name).collection(student_name).document("info")
    doc_ref.set({"chat_history": chat_history, "chat_summary": chat_summary, "instruction": instruction})
    print(f"Data of teacher chat info successfully added({teacher_name=}, {student_name=})")
  except PermissionDenied as e:
    print(f"Permission error: {e}")
  except GoogleAPICallError as e:
    print(f"Firestore API error: {e}")
  except Exception as e:
    print(f"Unexpected error: {e}")


# 先生と生徒用
# 先生とAI間のチャット履歴を取得する
def load_teacher_info(firebase_db: FirestoreClient, teacher_name: str, student_name: str) -> tuple[str, str]:
  doc_ref = firebase_db.collection("teachers").document(teacher_name).collection(student_name).document("info")

  doc = doc_ref.get()
  if doc.exists:
    history = doc.to_dict().get("chat_history", "")
    summary = doc.to_dict().get("chat_summary", "")
    instruction = doc.to_dict().get("instruction", "")
    return history, summary, instruction
  else:
    return "", "", ""
