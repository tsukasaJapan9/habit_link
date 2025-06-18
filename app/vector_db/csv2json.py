import json
import os

import pandas as pd

DIR = "./youtube_data/"
INPUT_FILE = os.path.join(DIR, "raw.csv")
OUTPUT_FILE = os.path.join(DIR, "fitness_video.json")

df = pd.read_csv(INPUT_FILE)
selected = df[["title", "description", "url", "user_input", "id"]]
json_data = selected.to_dict(orient="records")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
  json.dump(json_data, f, ensure_ascii=False, indent=2)
