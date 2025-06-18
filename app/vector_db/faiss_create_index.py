import json
import os
from uuid import uuid4

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

DIR = "youtube_data"
INDEX_DIR = "index"
INPUT_FILES = [
  "fitness_videos.json",
  "guiter_videos.json",
]

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-exp-03-07")

# LangChain Document のリストに変換
documents = []

os.makedirs(INDEX_DIR, exist_ok=True)

for file_name in INPUT_FILES:
  with open(os.path.join(DIR, file_name), "r", encoding="utf-8") as f:
    video_data = json.load(f)

  for item in video_data:
    # 現状youtubeの概要欄はとてもノイジーなのでタイトルを概要として扱う
    # ゆくゆくは動画の内容をちゃんと記述した概要を入れたい
    description = item.get("title", "").strip()
    if description:
      doc = Document(page_content=description, metadata={"title": item.get("title", ""), "url": item.get("url", "")})
      documents.append(doc)

  uuids = [str(uuid4()) for _ in range(len(documents))]

  faiss_index = FAISS.from_documents(documents, embeddings)

  # ローカル保存（永続化）
  name, _ = os.path.splitext(file_name)
  faiss_index.save_local(os.path.join(INDEX_DIR, f"{name}_index"))
