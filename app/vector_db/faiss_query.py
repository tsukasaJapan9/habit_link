from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-exp-03-07")


# FAISSをロード
faiss_index = FAISS.load_local(
  "faiss_index",
  embeddings,
  allow_dangerous_deserialization=True,
)

# 検索実行
query = "ギター"
results = faiss_index.similarity_search_with_score(query, k=3)

for res, score in results:
  print("-------------------------------")
  print(f"* [SIM={score:3f}]: [{res.page_content}, {res.metadata}]")
