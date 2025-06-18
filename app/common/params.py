import os
from datetime import timedelta, timezone

TEMPERATUE = 0.5
SEND_MSG_SIZE = 10
MAX_HISTORY_NUM = 30
DEBUG_MESSAGE_SIZE = 100
JST = timezone(timedelta(hours=9))

INF_SERVER_URL = os.getenv("LLM_API_URL", "http://localhost:8000")
HABIT_DESIGN_PATH = "./habit_design/habit_design_v2.txt"

STUDENT_PROMPT_GID = 1030669973
TEACHER_PROMPT_GID = 1598415957
