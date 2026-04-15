import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project root  (src/parking/config.py -> src/parking -> src -> root)
ROOT = Path(__file__).parent.parent.parent

# -------------------------------------------------------
# Database
# -------------------------------------------------------
DB_PATH = str(ROOT / os.getenv("DB_PATH", "dynamic_parking.db"))

# -------------------------------------------------------
# Security
# -------------------------------------------------------
FASTAPI_KEY = os.getenv("FASTAPI_KEY")
if not FASTAPI_KEY:
    raise ValueError("FASTAPI_KEY is not set — add it to your .env file")

# -------------------------------------------------------
# Service URLs
# -------------------------------------------------------
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000")
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8180")

# -------------------------------------------------------
# LLM
# -------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
