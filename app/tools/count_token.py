from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

TEMPERATUE = 0.5
model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=TEMPERATUE)

with open("../habit_design/habit_desgin_original.txt") as f:
  input_data = f.read()

messages = [SystemMessage(content=input_data)]
num_tokens = model.get_num_tokens_from_messages(messages)

print(num_tokens)
