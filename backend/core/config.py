"""
EMO Backend - Configuration
============================
Centralized configuration for LLM, paths, and settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# LLM CONFIGURATION
# =============================================================================

# Gemini API - Gemma 3 27B with manual function calling
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMMA_27B_MODEL = "gemma-3-27b-it"  # Gemma 3 27B with manual function calling

# LitGPT / Lightning Studio
LITGPT_API_KEY = os.getenv("LITGPT_API_KEY")
LITGPT_API_BASE = os.getenv("LITGPT_API_BASE", "https://your-litgpt-instance.lightning.ai/v1")
LITGPT_MODEL = os.getenv("LITGPT_MODEL", "iJoshNh/EmoN3")

# LLM Provider Selection: "gemini" or "litgpt"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")

TEMPERATURE = 0.3  # Lower for faster, more focused responses

# Generation settings (OPTIMIZED for speed)
MAX_OUTPUT_TOKENS = 2048  # Increased for function calling responses
TITLE_MAX_TOKENS = 50
REQUEST_TIMEOUT = 30  # 30 second timeout

# =============================================================================
# PATHS
# =============================================================================

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
USER_CONFIG_FILE = DATA_DIR / "user_config.json"
TODO_FILE = DATA_DIR / "todo.json"
CHROMA_PATH = str(DATA_DIR / "emo_memory")
CREDENTIALS_FILE = DATA_DIR / "credentials.json"
GMAIL_TOKEN_FILE = DATA_DIR / "gmail_token.json"
CALENDAR_TOKEN_FILE = DATA_DIR / "calendar_token.json"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# =============================================================================
# SESSION LIMITS
# =============================================================================

MAX_MESSAGES_PER_SESSION = 30
WARNING_THRESHOLD = 25

# =============================================================================
# GOOGLE API SCOPES
# =============================================================================

GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
]

CALENDAR_SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
]
