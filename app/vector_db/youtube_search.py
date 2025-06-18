import json
import os

import requests

API_KEY = os.environ.get("GOOGLE_API_KEY", "")
SEARCH_QUERY = "bob marley guiter 練習"
MAX_RESULTS = 30
OUTPUT_FILENAME = "youtube_data/guiter_videos_raw.json"

search_url = "https://www.googleapis.com/youtube/v3/search"
video_url = "https://www.googleapis.com/youtube/v3/videos"

# ステップ1: 動画IDの取得（検索）
search_params = {"part": "snippet", "q": SEARCH_QUERY, "type": "video", "maxResults": MAX_RESULTS, "key": API_KEY}

search_res = requests.get(search_url, params=search_params).json()
video_ids = [item["id"]["videoId"] for item in search_res["items"]]

# ステップ2: 動画情報の取得（詳細）
video_params = {"part": "snippet", "id": ",".join(video_ids), "key": API_KEY}

video_res = requests.get(video_url, params=video_params).json()

# 結果出力
videos = []
for item in video_res["items"]:
  video = {
    "title": item["snippet"]["title"],
    "description": item["snippet"]["description"],
    "url": f"https://www.youtube.com/watch?v={item['id']}",
  }
  videos.append(video)

# 確認
for v in videos:
  print(v["title"])
  print(v["url"])
  print(v["description"][:100], "\n")

with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
  json.dump(videos, f, ensure_ascii=False, indent=4)
