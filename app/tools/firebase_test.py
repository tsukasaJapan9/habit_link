from datetime import datetime, timedelta, timezone

import firebase_admin
from firebase_admin import firestore
from google.cloud.firestore_v1 import FieldFilter

JST = timezone(timedelta(hours=9))

app = firebase_admin.initialize_app(options={"projectId": "habit-agent"})
db = firestore.client()

user_id = "tsukasa"
date = datetime(2025, 4, 28)
start_time = datetime(2025, 4, 28, 18, 0)
end_time = datetime(2025, 4, 28, 18, 45)


# traning typeを追加
exercise_data = {
  "date": date.strftime("%Y-%m-%d"),
  "start_time": start_time.strftime("%H:%M:%S"),
  "end_time": end_time.strftime("%H:%M:%S"),
  # "traning_type": ""
  "created_at": datetime.now(),
}

# 運動データをFirestoreに保存
# db.collection("users").document(user_id).collection("exercise_logs").add(exercise_data)

# # データ保存後、保存した運動データを読み取るコード
# # 特定のユーザの運動記録を取得
# exercise_logs_ref = db.collection("users").document(user_id).collection("exercise_logs")

# # 運動記録をクエリで取得（降順で並べる、または他のフィルタリングが可能）
# docs = exercise_logs_ref.order_by("created_at", direction=firestore.Query.DESCENDING).stream()


def load_exercise_data(user_name: str):
  # DBにはUTCで保存されている
  now_utc = datetime.now(tz=timezone.utc)
  one_month_ago = now_utc - timedelta(days=30)

  month_ago_ts = one_month_ago.timestamp()

  logs_ref = db.collection("users").document(user_name).collection("exercise_logs")
  query = logs_ref.where(filter=FieldFilter("start_time", ">=", month_ago_ts)).order_by(
    "start_time", direction=firestore.Query.DESCENDING
  )
  docs = query.stream()
  return docs


docs = load_exercise_data(user_id)

# 取得した運動記録を表示
for doc in docs:
  print(f"運動記録: {doc.to_dict()}")
  print(
    datetime.fromtimestamp(doc.to_dict()["created_at"], tz=JST),
    datetime.fromtimestamp(doc.to_dict()["start_time"], tz=JST),
  )
