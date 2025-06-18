#!/bin/bash

#uv run streamlit run ui.py --server.headless true --logger.level=debug
uv run streamlit run ui.py --server.port $PORT --server.headless true
