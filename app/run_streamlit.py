#!/bin/bash

#uv run streamlit run ui.py --server.headless true --logger.level=debug
uv run streamlit run minimum_streamlit.py --server.port $PORT --logger.level DEBUG
