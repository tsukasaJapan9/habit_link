import json
import os
import re

import emoji

DIR = "youtube_data"
INPUT_FILE = os.path.join(DIR, "guiter_videos_raw.json")
OUTPUT_FILE = os.path.join(DIR, "guiter_videos.json")


def clean_description(text: str) -> str:
  # httpリンクを削除
  text = re.sub(r"http\S+", "", text)
  # メンション削除（@から始まる単語）
  text = re.sub(r"@[\w\-_.]+", "", text)
  # 改行削除
  text = text.replace("\n", " ")
  # 絵文字削除
  text = emoji.replace_emoji(text, replace="")
  # 空白を整える
  text = re.sub(r"\s+", " ", text).strip()
  return text


# txtファイル読み込み
with open(INPUT_FILE, "r", encoding="utf-8") as f:
  data = json.load(f)

# descriptionを加工
for item in data:
  item["description"] = clean_description(item["description"])

print(data[2])

# 加工済みデータをjsonで保存
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
  json.dump(data, f, ensure_ascii=False, indent=2)

print(f"saved: {OUTPUT_FILE}")
