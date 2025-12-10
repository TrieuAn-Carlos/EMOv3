"""
EMO Backend - Calendar Integration
===================================
Google Calendar API - no Streamlit dependencies.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Any
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Configuration
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events'
]
BASE_DIR = Path(__file__).parent.parent
CREDENTIALS_FILE = BASE_DIR / 'credentials.json'
TOKEN_FILE = BASE_DIR / 'data' / 'calendar_token.json'

# In-memory cache
_calendar_service = None


def authenticate_calendar() -> Any:
    """Authenticate with Google Calendar API using OAuth 2.0."""
    global _calendar_service
    
    creds = None
    
    # Check for saved token
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception:
            pass
    
    # Refresh or create new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        
        if not creds:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(f"'{CREDENTIALS_FILE}' not found.")
            
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save token
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
    
    _calendar_service = build('calendar', 'v3', credentials=creds)
    return _calendar_service


def get_calendar_service() -> Any:
    """Get or create Calendar service instance."""
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = authenticate_calendar()
    return _calendar_service


def disconnect_calendar() -> bool:
    """Disconnect Calendar."""
    global _calendar_service
    _calendar_service = None
    
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
    return True


def is_calendar_connected() -> bool:
    """Check if Calendar is connected."""
    return TOKEN_FILE.exists()


def list_upcoming_events(days: int = 7, max_results: int = 10) -> str:
    """List upcoming calendar events."""
    try:
        service = get_calendar_service()
        
        now = datetime.utcnow()
        time_min = now.isoformat() + 'Z'
        time_max = (now + timedelta(days=days)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return f"📅 No upcoming events in the next {days} day(s)."
        
        output = [f"📅 **Upcoming Events** (next {days} days):", ""]
        
        for i, event in enumerate(events, 1):
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'Untitled Event')
            location = event.get('location', '')
            
            if 'T' in start:
                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                formatted_time = dt.strftime('%a %b %d, %H:%M')
            else:
                formatted_time = start
            
            event_line = f"{i}. **{summary}** — {formatted_time}"
            if location:
                event_line += f" 📍 {location}"
            
            output.append(event_line)
        
        return "\n".join(output)
    
    except FileNotFoundError as e:
        return f"❌ {str(e)}"
    except Exception as e:
        if "invalid_grant" in str(e).lower():
            disconnect_calendar()
            return "❌ Calendar token expired. Please reconnect."
        return f"❌ Error: {str(e)}"


def search_events(query: str, days: int = 30) -> str:
    """Search calendar events by keyword."""
    try:
        service = get_calendar_service()
        
        now = datetime.utcnow()
        time_min = (now - timedelta(days=days)).isoformat() + 'Z'
        time_max = (now + timedelta(days=days)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            q=query,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return f"🔍 No events found matching '{query}'."
        
        output = [f"🔍 Found {len(events)} event(s) matching '{query}':", ""]
        
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'Untitled')
            
            if 'T' in start:
                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                formatted = dt.strftime('%a %b %d, %H:%M')
            else:
                formatted = start
            
            output.append(f"• **{summary}** — {formatted}")
        
        return "\n".join(output)
    
    except Exception as e:
        return f"❌ Error: {str(e)}"


def quick_add_event(text: str) -> str:
    """Create event using natural language (Google's Quick Add)."""
    try:
        service = get_calendar_service()
        
        created_event = service.events().quickAdd(
            calendarId='primary',
            text=text
        ).execute()
        
        summary = created_event.get('summary', 'Event')
        start = created_event['start'].get('dateTime', created_event['start'].get('date', ''))
        
        if start and 'T' in start:
            dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            formatted = dt.strftime('%A, %b %d at %H:%M')
        else:
            formatted = start
        
        return (
            f"✅ Event created: **{summary}**\n"
            f"📅 {formatted}\n"
            f"🔗 [View in Calendar]({created_event.get('htmlLink', '')})"
        )
    
    except Exception as e:
        return f"❌ Error: {str(e)}"


def create_event(
    summary: str,
    start_time: str,
    end_time: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None
) -> str:
    """Create a new calendar event."""
    try:
        service = get_calendar_service()
        
        try:
            start_dt = datetime.fromisoformat(start_time)
        except ValueError:
            return f"❌ Invalid start time: {start_time}. Use ISO format."
        
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time)
            except ValueError:
                end_dt = start_dt + timedelta(hours=1)
        else:
            end_dt = start_dt + timedelta(hours=1)
        
        event = {
            'summary': summary,
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Ho_Chi_Minh'},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Ho_Chi_Minh'},
        }
        
        if description:
            event['description'] = description
        if location:
            event['location'] = location
        
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        
        return (
            f"✅ Event created: **{summary}**\n"
            f"📅 {start_dt.strftime('%A, %b %d at %H:%M')}\n"
            f"🔗 [View in Calendar]({created_event.get('htmlLink', '')})"
        )
    
    except Exception as e:
        return f"❌ Error: {str(e)}"
