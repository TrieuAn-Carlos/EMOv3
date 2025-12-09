"""
EMO Backend - Auth Router
=========================
OAuth for Gmail and Calendar using InstalledAppFlow (desktop OAuth).
"""

import os
import json
import threading
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

router = APIRouter()

# Configuration
BASE_DIR = Path(__file__).parent.parent
CREDENTIALS_FILE = BASE_DIR.parent.parent / 'credentials.json'
GMAIL_TOKEN_FILE = BASE_DIR / 'data' / 'gmail_token.json'
CALENDAR_TOKEN_FILE = BASE_DIR / 'data' / 'calendar_token.json'

GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/calendar.events']

# Track OAuth in progress
_oauth_in_progress = {"gmail": False, "calendar": False}


class ConnectionStatus(BaseModel):
    """Connection status for services."""
    gmail: bool = False
    calendar: bool = False


def check_token_valid(token_file: Path, scopes: list) -> bool:
    """Check if a token file exists and is valid."""
    if not token_file.exists():
        return False
    try:
        creds = Credentials.from_authorized_user_file(str(token_file), scopes)
        if creds and creds.valid:
            return True
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                token_file.parent.mkdir(parents=True, exist_ok=True)
                with open(token_file, 'w') as f:
                    f.write(creds.to_json())
                return True
            except:
                return False
    except:
        pass
    return False


def run_oauth_flow(scopes: list, token_file: Path, service_name: str):
    """Run OAuth flow in background thread."""
    try:
        _oauth_in_progress[service_name] = True
        
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE),
            scopes=scopes
        )
        
        # This opens browser automatically and waits for callback
        creds = flow.run_local_server(
            port=0,  # Use random available port
            success_message="✅ Authorization successful! You can close this window and return to EMO.",
            open_browser=True
        )
        
        # Save token
        token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(token_file, 'w') as f:
            f.write(creds.to_json())
            
        print(f"✅ {service_name} OAuth completed successfully")
        
    except Exception as e:
        print(f"❌ {service_name} OAuth failed: {e}")
    finally:
        _oauth_in_progress[service_name] = False


@router.get("/status")
async def get_connection_status():
    """Check which services are connected."""
    return ConnectionStatus(
        gmail=check_token_valid(GMAIL_TOKEN_FILE, GMAIL_SCOPES),
        calendar=check_token_valid(CALENDAR_TOKEN_FILE, CALENDAR_SCOPES),
    )


@router.get("/gmail/connect")
async def start_gmail_oauth():
    """Start Gmail OAuth flow - opens browser automatically."""
    if not CREDENTIALS_FILE.exists():
        raise HTTPException(status_code=500, detail="OAuth credentials.json not found")
    
    if check_token_valid(GMAIL_TOKEN_FILE, GMAIL_SCOPES):
        return {"status": "already_connected", "message": "Gmail is already connected"}
    
    if _oauth_in_progress["gmail"]:
        return {"status": "in_progress", "message": "OAuth already in progress, check your browser"}
    
    # Run OAuth in background thread so API doesn't block
    thread = threading.Thread(
        target=run_oauth_flow,
        args=(GMAIL_SCOPES, GMAIL_TOKEN_FILE, "gmail"),
        daemon=True
    )
    thread.start()
    
    return {
        "status": "started",
        "message": "OAuth started - a browser window should open. Complete authorization there."
    }


@router.get("/calendar/connect")
async def start_calendar_oauth():
    """Start Calendar OAuth flow - opens browser automatically."""
    if not CREDENTIALS_FILE.exists():
        raise HTTPException(status_code=500, detail="OAuth credentials.json not found")
    
    if check_token_valid(CALENDAR_TOKEN_FILE, CALENDAR_SCOPES):
        return {"status": "already_connected", "message": "Calendar is already connected"}
    
    if _oauth_in_progress["calendar"]:
        return {"status": "in_progress", "message": "OAuth already in progress, check your browser"}
    
    thread = threading.Thread(
        target=run_oauth_flow,
        args=(CALENDAR_SCOPES, CALENDAR_TOKEN_FILE, "calendar"),
        daemon=True
    )
    thread.start()
    
    return {
        "status": "started",
        "message": "OAuth started - a browser window should open. Complete authorization there."
    }


@router.post("/gmail/disconnect")
async def disconnect_gmail():
    """Disconnect Gmail by removing token."""
    if GMAIL_TOKEN_FILE.exists():
        GMAIL_TOKEN_FILE.unlink()
    return {"status": "disconnected"}


@router.post("/calendar/disconnect")
async def disconnect_calendar():
    """Disconnect Calendar by removing token."""
    if CALENDAR_TOKEN_FILE.exists():
        CALENDAR_TOKEN_FILE.unlink()
    return {"status": "disconnected"}
