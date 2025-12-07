"""
EMO2 - Calendar Tools
=====================
Google Calendar API integration for listing, searching, and creating events.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from credentials_manager import (
    store_account, get_primary_account, is_connected
)

# Calendar API scopes
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events'
]
CREDENTIALS_FILE = 'calendar_credentials.json'
TOKEN_FILE = 'calendar_token.json'


def authenticate_calendar() -> Any:
    """Authenticate with Google Calendar API using OAuth 2.0."""
    creds = None
    
    # Check credentials manager first
    account = get_primary_account('calendar')
    if account and account.get('token'):
        try:
            creds = Credentials.from_authorized_user_info(account['token'], SCOPES)
        except Exception:
            pass
    
    # Fall back to token file
    if not creds and os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"'{CREDENTIALS_FILE}' not found. "
                    "Download OAuth credentials from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save token
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        
        # Get user email and store in credentials manager
        try:
            service = build('calendar', 'v3', credentials=creds)
            calendar = service.calendars().get(calendarId='primary').execute()
            email = calendar.get('id', 'unknown@gmail.com')
            store_account('calendar', email, creds.to_json())
        except Exception:
            pass
    
    return build('calendar', 'v3', credentials=creds)


def get_calendar_service() -> Any:
    """Get or create Calendar service instance."""
    if 'calendar_service' not in st.session_state:
        st.session_state.calendar_service = authenticate_calendar()
    return st.session_state.calendar_service


def disconnect_calendar() -> bool:
    """Disconnect Calendar by clearing cached service and token."""
    try:
        if 'calendar_service' in st.session_state:
            del st.session_state.calendar_service
        
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        return True
    except Exception:
        return False


def test_calendar_connection() -> tuple[bool, str]:
    """Test Calendar connection. Returns (success, message)."""
    try:
        service = get_calendar_service()
        calendar = service.calendars().get(calendarId='primary').execute()
        return True, f"Connected to: {calendar.get('summary', 'Primary Calendar')}"
    except Exception as e:
        return False, f"Error: {str(e)[:50]}"


def list_upcoming_events(days: int = 7, max_results: int = 10) -> str:
    """
    List upcoming calendar events.
    
    Args:
        days: Number of days to look ahead
        max_results: Maximum events to return
        
    Returns:
        Formatted string of upcoming events
    """
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
        
        output = [f"📅 **Upcoming Events** (next {days} days):"]
        output.append("")
        
        for i, event in enumerate(events, 1):
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'Untitled Event')
            location = event.get('location', '')
            
            # Parse and format datetime
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
        return f"❌ Error fetching calendar: {str(e)}"


def search_events(query: str, days: int = 30) -> str:
    """
    Search calendar events by keyword.
    
    Args:
        query: Search term
        days: Number of days to search (past and future)
        
    Returns:
        Formatted string of matching events
    """
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
        
        output = [f"🔍 Found {len(events)} event(s) matching '{query}':"]
        output.append("")
        
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
        return f"❌ Error searching calendar: {str(e)}"


def create_event(
    summary: str,
    start_time: str,
    end_time: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None
) -> str:
    """
    Create a new calendar event.
    
    Args:
        summary: Event title
        start_time: Start time (ISO format or natural language)
        end_time: End time (defaults to 1 hour after start)
        description: Event description
        location: Event location
        
    Returns:
        Confirmation message
    """
    try:
        service = get_calendar_service()
        
        # Parse start time
        try:
            start_dt = datetime.fromisoformat(start_time)
        except ValueError:
            return f"❌ Invalid start time format: {start_time}. Use ISO format (YYYY-MM-DDTHH:MM:SS)."
        
        # Default end time is 1 hour after start
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
        return f"❌ Error creating event: {str(e)}"


def quick_add_event(text: str) -> str:
    """
    Create an event using natural language (Google's Quick Add).
    
    Args:
        text: Natural language event description
              e.g., "Meeting with John tomorrow at 3pm"
              
    Returns:
        Confirmation message
    """
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
        return f"❌ Error creating event: {str(e)}"


def get_today_events() -> str:
    """Get today's calendar events."""
    return list_upcoming_events(days=1, max_results=20)


def get_week_events() -> str:
    """Get this week's calendar events."""
    return list_upcoming_events(days=7, max_results=20)
