from dataclasses import dataclass
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("video_search")


@dataclass
class SearchResult:
  url: str
  description: str
  similarity: float


# FAISSをロード
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-exp-03-07")
faiss_index = FAISS.load_local(
  "vector_db/faiss_index",
  embeddings,
  allow_dangerous_deserialization=True,
)


@mcp.tool()
async def video_search(search_query: str, result_num: int) -> list[Any]:
  """
  Search for information on videos similar to query from a database
  containing vector data of videos.
  Use this Tool when users are looking for video data.

  Args:
    search_query: Search keyword.
    result_num: Number of search results.

  Returns:
    Top search results.
  """
  result_num = min(result_num, 3)

  top_ranks: list[SearchResult] = []
  # results = google_custom_search_dummy(search_query)
  # results = google_custom_search(search_query)
  results = faiss_index.similarity_search_with_score(search_query, k=result_num)

  for result, similarity in results:
    top_ranks.append(
      SearchResult(
        url=result.metadata["url"],
        description=result.page_content,
        similarity=similarity,
      )
    )
  return top_ranks


if __name__ == "__main__":
  # import asyncio
  # result = asyncio.run(search("ダイエットのやり方", 3))
  # print(result)
  mcp.run(transport="stdio")
