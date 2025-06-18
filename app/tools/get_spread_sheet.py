import os

import pandas as pd

# for student
# gid = 950493141

# for teacher
gid = 1995665672

SPREAD_SHEET_URL = os.environ["SPREAD_SHEET_URL"]


def get_system_prompt(phase: int, gid: int) -> str:
  url = f"{SPREAD_SHEET_URL}&gid={gid}"
  df = pd.read_csv(url, header=None)
  prompt = ""
  for _, row in df.iterrows():
    if "phase" in row.iloc[0] and f"phase{phase}" not in row.iloc[0]:
      continue

    prompt += row.iloc[1]
    prompt += "\n-------------------------\n"

  return prompt


print(get_system_prompt(phase=1, gid=gid))
