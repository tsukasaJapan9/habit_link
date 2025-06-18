import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from streamlit_calendar import calendar

calendar_id = 0


def show_chat_history(messages):
  global calendar_id
  for message in messages:
    content = message.content
    if isinstance(message, AIMessage):
      with st.chat_message("Assistant"):
        st.markdown(content)
    elif isinstance(message, HumanMessage):
      if message.name == "calendar":
        calendar(key=f"calendar_{calendar_id}")
        calendar_id += 1
      else:
        with st.chat_message("User"):
          st.markdown(content)
      # with st.chat_message("User"):
      #   st.markdown(content)
    elif isinstance(message, ToolMessage):
      with st.chat_message("Tool"):
        try:
          content = ast.literal_eval(content)
          content = [json.loads(c) for c in content]
        except (SyntaxError, ValueError):
          content = message.content
        st.markdown(content)
    else:
      with st.chat_message("system"):
        st.markdown(content)


messages = [
  AIMessage(content="test1"),
  HumanMessage(content="test2"),
  AIMessage(content="test3"),
  HumanMessage(content="test4", name="calendar"),
  HumanMessage(content="test5"),
  AIMessage(content="test6"),
  HumanMessage(content="test7", name="calendar"),
  HumanMessage(content="test8"),
  AIMessage(content="test9"),
]

show_chat_history(messages)

# st.set_page_config(page_title="Chat App")
# st.title("Habit Agent")

# st.markdown("test1")
# st.markdown("test2")


# calendar(key="1")

# st.markdown("test3")
# st.markdown("test4")

# calendar(key="2")

# st.markdown("test5")
# st.markdown("test6")
