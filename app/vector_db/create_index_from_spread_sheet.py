import os
import time
from collections import defaultdict

import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

SPREAD_SHEET_URL = os.environ["SPREAD_SHEET_URL"]
GID = 1442759695


embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-exp-03-07")

# {category: video_info[(title, url)]}
video_data = defaultdict(list)
indexes = []

url = f"{SPREAD_SHEET_URL}&gid={GID}"
df = pd.read_csv(url)
for _, row in df.iterrows():
  # (description, url)
  video_data[row.iloc[0]].append((row.iloc[2], row.iloc[1]))

for category, data in video_data.items():
  print(f"----- creating index for {category}(num: {len(data)}) -----")
  documents = []
  for d in data:
    doc = Document(page_content=d[0], metadata={"url": d[1], "category": category})
    documents.append(doc)
  index = FAISS.from_documents(documents, embeddings)
  indexes.append(index)

  # 一気にindexを作るとAPI制限に引っかかるのでスリープ
  time.sleep(5)

if len(indexes) == 0:
  print("Index is not found")
  exit(1)

if len(indexes) == 1:
  indexes[0].save_local("faiss_index")

merged_index = indexes[0]

for index in indexes[1:]:
  merged_index.merge_from(index)

merged_index.save_local("faiss_index")
