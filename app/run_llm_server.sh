#!/bin/bash

#uv run uvicorn llm_server:app --host 0.0.0.0 --port $PORT --reload
uv run uvicorn llm_server:app --host 0.0.0.0 --port $PORT
#uv run uvicorn llm_server:app
