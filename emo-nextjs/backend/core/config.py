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

# Groq API (primary)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"  # Production model: 280 T/s, 131K context
TEMPERATURE = 0.3  # Lower for faster, more focused responses

# Gemini API (primary fallback)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash-exp"  # Latest fast model
# Gemma 3 27B (via Gemini API) - Manual function calling
GEMMA_27B_MODEL = "gemma-3-27b-it"  # Gemma 3 27B Instruction-tuned
USE_GEMMA = os.getenv("USE_GEMMA", "false").lower() == "true"  # Toggle for Gemma

# Generation settings (OPTIMIZED for speed)
MAX_OUTPUT_TOKENS = 1024  # Reduced from 4096 for faster generation
TITLE_MAX_TOKENS = 50
REQUEST_TIMEOUT = 30  # 30 second timeout
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
