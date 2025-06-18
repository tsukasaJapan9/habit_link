import ast
import json
import os
from contextlib import AsyncExitStack

from fastapi import FastAPI
from langchain_core.messages import ToolMessage
from langchain_core.messages.base import messages_to_dict
from langchain_core.messages.utils import messages_from_dict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.resources import load_mcp_resources
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel

# for langsmith
os.environ["LANGCHAIN_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGSMITH_PROJECT"] = "habit_agent"

GOOGLE_CUSTOM_SEARCH_API_KEY = os.environ["GOOGLE_CUSTOM_SEARCH_API_KEY"]
GOOGLE_CUSTOM_SEARCH_ENGINE_ID = os.environ["GOOGLE_CUSTOM_SEARCH_ENGINE_ID"]

CONFIG_PATH = "./config/config.json"

DEBUG_MESSAGE_SIZE = 100
TEMPERATUE = 0.5


class UserInput(BaseModel):
  message: str


app = FastAPI()

exit_stack = AsyncExitStack()
agent = None
model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=TEMPERATUE)
# 2.5 flashはかなり遅い
# model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-05-20", temperature=TEMPERATUE)
tools = []
resources = []


@app.on_event("startup")
async def startup_event():
  global exit_stack, agent, tools, resources

  with open(CONFIG_PATH) as f:
    config_data = json.load(f)
  mcp_servers = config_data["mcpServers"]

  await exit_stack.__aenter__()
  print("MCP server initializing")
  for server_name, server_info in mcp_servers.items():
    print(f"--------------- {server_name} ---------------")

    if "env" in server_info:
      env = {k: os.environ[v] for k, v in server_info["env"].items()}
    else:
      env = {}

    is_docker = os.path.exists("/DOCKER")
    command = "uv" if is_docker else server_info["command"]
    server_params = StdioServerParameters(
      command=command,
      args=server_info["args"],
      env=env,
    )
    read_stream, write_stream = await exit_stack.enter_async_context(stdio_client(server_params))
    session = await exit_stack.enter_async_context(ClientSession(read_stream, write_stream))

    await session.initialize()

    server_tools = await load_mcp_tools(session)
    print("<Available tools>")
    for tool in server_tools:
      print(f" - {tool.name}: {tool.description}")
      tools.append(tool)

    server_resources = await load_mcp_resources(session)
    print("<Available resources>")
    for resource in server_resources:
      print(f" - {resource.data}, {resource.mimetype}, {resource.metadata}")
      resources.append(resource)

  agent = create_react_agent(model, tools)


@app.on_event("shutdown")
async def shutdown():
  global exit_stack
  await exit_stack.__aexit__(None, None, None)


@app.post("/infer")
async def infer(input_data: UserInput):
  global agent

  print("=============================================")
  # ユーザからの入力はAPI経由でjsonでくるのでlangchainのメッセージオブジェクトに変換
  messages = messages_from_dict(json.loads(input_data.message))

  print("---------- [infer server]: user input data from ui ----------")
  for message in messages:
    print(f"{message.__class__.__name__}: {message.content[:DEBUG_MESSAGE_SIZE]}")

  agent_response = await agent.ainvoke({"messages": messages})
  agent_response = agent_response["messages"]

  print("---------- [infer server]: ai agent response ----------")

  for message in agent_response:
    # デバッグ表示のために形式を変換
    if isinstance(message, ToolMessage):
      try:
        contents = ast.literal_eval(message.content)
        contents = [json.loads(content) for content in contents]
      except (SyntaxError, ValueError):
        contents = message.content
    else:
      contents = message.content

    print(f"{message.__class__.__name__}: {contents[:DEBUG_MESSAGE_SIZE]}, {type(message)}")

  # langchainのinvokeで得たデータはメッセージオブジェクトなのでjsonに変換
  json_data = messages_to_dict(agent_response)
  json_str = json.dumps(json_data, indent=2)
  return {"response": json_str}


@app.get("/tools")
def get_tools() -> dict[str, str]:
  _tools = {tool.name: tool.description for tool in tools}
  return {"tools": json.dumps(_tools, indent=2)}
