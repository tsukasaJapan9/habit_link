import os
from dataclasses import dataclass
from typing import Any

import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

GOOGLE_CUSTOM_SEARCH_API_KEY = os.environ["GOOGLE_CUSTOM_SEARCH_API_KEY"]
GOOGLE_CUSTOM_SEARCH_ENGINE_ID = os.environ["GOOGLE_CUSTOM_SEARCH_ENGINE_ID"]


@dataclass
class SearchResultSummary:
  title: str
  url: str
  description: str


mcp = FastMCP("web_search")


def google_custom_search(query: str, num_results: int = 3) -> list[Any]:
  url = "https://www.googleapis.com/customsearch/v1"
  params: dict[str, Any] = {
    "key": GOOGLE_CUSTOM_SEARCH_API_KEY,
    "cx": GOOGLE_CUSTOM_SEARCH_ENGINE_ID,
    "q": query,
    "num": num_results,
  }

  response = requests.get(url, params=params)
  if response.status_code != 200:
    print(f"Error: {response.status_code} - {response.text}")
    return []

  results = response.json().get("items", [])
  top_results = []
  for item in results:
    top_results.append(
      {
        "title": item.get("title"),
        "link": item.get("link"),
        "snippet": item.get("snippet"),
      }
    )

  return top_results


def google_custom_search_dummy(query: str, num_results: int = 3) -> list[Any]:
  top_results = []
  for i in range(num_results):
    top_results.append(
      {
        "title": f"{i}: title",
        "link": f"{i}: link",
        "snippet": f"{i}: description",
      }
    )

  return top_results


@mcp.tool()
async def search_and_pickup_top_results(search_query: str) -> list[Any]:
  """
  Search for articles on the internet using
  google custom web search api.
  If you have any questions from users that you don't understand,
  please use this function to search for them!

  Args:
    search_query: Search keyword.

  Returns:
    Overview of top search results.
  """
  top_ranks = []
  # results = google_custom_search_dummy(search_query)
  results = google_custom_search(search_query)

  print("---------------------------------------------------------------")
  print("search result")
  print(results)
  print("---------------------------------------------------------------")

  for result in results:
    top_ranks.append(
      SearchResultSummary(
        title=str(result["title"]),
        url=result["link"],
        description=result["snippet"],
      )
    )
  return top_ranks


@mcp.tool()
async def get_url_contents(url: str) -> str:
  """
  Returns the contents of the page at the given URL as a string.
  Use this to find out about the contents of a specific URL.

  Args:
    url: Web page URL.

  Returns:
    Contents of the page at the given URL.
  """
  result = ""
  try:
    response = requests.get(url)
    response.encoding = response.apparent_encoding
    html = response.text

    # htmlのパース
    soup = BeautifulSoup(html, "html.parser")

    # htmlタグを除去して内容をテキスト化
    text = soup.get_text(separator="\n", strip=True)
    result = "\n".join(line for line in text.splitlines() if line.strip())
  except Exception as e:
    print(f"Failed to get contents({url}): {e}")
    result = f"ページの内容取得に失敗しました({url})"
  return result


if __name__ == "__main__":
  # import asyncio

  # result = asyncio.run(get_url_contents("https://www.npr.org/sections/strange-news/"))
  # print(result)
  # asyncio.run(get_url_contents("https://www3.nhk.or.jp/news/catnew.html"))
  mcp.run(transport="stdio")
