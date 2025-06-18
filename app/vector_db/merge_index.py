import os

from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-exp-03-07")

INDEX_DIR = "index"

index_names = os.listdir(INDEX_DIR)
if len(index_names) == 0:
  print("Index is not found")
  exit(1)

if len(index_names) == 1:
  print("There is only one index. There is no need to merge them.")
  exit(1)

indexes = []

for index_name in index_names:
  indexes.append(
    FAISS.load_local(
      os.path.join(INDEX_DIR, index_name),
      embeddings=embeddings,
      allow_dangerous_deserialization=True,
    )
  )

merged_index = indexes[0]

for index in indexes[1:]:
  merged_index.merge_from(index)

merged_index.save_local("merged_index")
