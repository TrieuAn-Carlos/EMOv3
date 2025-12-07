"""
EMO2 - Gmail Tools
==================
Gmail authentication, email search, and attachment handling.
"""

import os
import re
import base64
from typing import List, Tuple, Optional

import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from parsers import parse_attachment
from credentials_manager import store_account, get_primary_account

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'


def authenticate_gmail():
    """Authenticate with Gmail API using OAuth 2.0."""
    creds = None
    
    # Check credentials manager first
    account = get_primary_account('gmail')
    if account and account.get('token'):
        try:
            import json
            token_data = account['token']
            if isinstance(token_data, str):
                token_data = json.loads(token_data)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
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
                raise FileNotFoundError(f"'{CREDENTIALS_FILE}' not found")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save token to file (legacy)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        
        # Save to credentials manager
        try:
            service = build('gmail', 'v1', credentials=creds)
            profile = service.users().getProfile(userId='me').execute()
            email = profile.get('emailAddress', 'unknown@gmail.com')
            import json
            store_account('gmail', email, json.loads(creds.to_json()))
        except Exception:
            pass
    
    return build('gmail', 'v1', credentials=creds)


def get_gmail_service():
    """Get or create Gmail service instance."""
    if 'gmail_service' not in st.session_state:
        st.session_state.gmail_service = authenticate_gmail()
    return st.session_state.gmail_service


def disconnect_gmail():
    """Disconnect Gmail by clearing cached service and token."""
    try:
        if 'gmail_service' in st.session_state:
            del st.session_state.gmail_service
        st.session_state.gmail_authenticated = False
        
        token_path = os.path.join(os.path.dirname(__file__), 'token.json')
        if os.path.exists(token_path):
            os.remove(token_path)
        return True
    except Exception:
        return False


def reconnect_gmail():
    """Force reconnect to Gmail."""
    try:
        if 'gmail_service' in st.session_state:
            del st.session_state.gmail_service
        
        service = authenticate_gmail()
        if service:
            st.session_state.gmail_service = service
            st.session_state.gmail_authenticated = True
            return True
        return "Authentication failed"
    except Exception as e:
        st.session_state.gmail_authenticated = False
        return str(e)


def test_gmail_connection():
    """Test Gmail connection. Returns (success, message)."""
    try:
        service = get_gmail_service()
        results = service.users().messages().list(
            userId='me', q='newer_than:1d', maxResults=1
        ).execute()
        count = len(results.get('messages', []))
        return True, f"Connected! Found {count} email(s) from today."
    except Exception as e:
        return False, f"Error: {str(e)[:50]}"


def extract_gmail_query(user_message: str) -> str:
    """Extract optimal Gmail search query from natural language."""
    msg_lower = user_message.lower()
    query_parts = []
    
    # Time keywords
    if any(w in msg_lower for w in ['today', 'hôm nay']):
        query_parts.append('newer_than:1d')
    elif any(w in msg_lower for w in ['yesterday', 'hôm qua']):
        query_parts.append('newer_than:2d older_than:1d')
    elif any(w in msg_lower for w in ['this week', 'tuần này']):
        query_parts.append('newer_than:7d')
    elif any(w in msg_lower for w in ['this month', 'tháng này']):
        query_parts.append('newer_than:30d')
    
    # Extract quoted terms
    quoted = re.findall(r'"([^"]+)"', user_message)
    for term in quoted:
        query_parts.append(f'"{term}"')
    
    # Extract from: patterns
    from_match = re.search(r'from\s+([a-zA-Z0-9@.]+)', msg_lower)
    if from_match:
        query_parts.append(f'from:{from_match.group(1)}')
    
    # Extract subject patterns
    subj_match = re.search(r'subject:\s*([^\s]+)', msg_lower)
    if subj_match:
        query_parts.append(f'subject:{subj_match.group(1)}')
    
    # Keywords
    skip_words = {'email', 'find', 'search', 'show', 'get', 'my', 'the', 'about', 'from', 'to'}
    words = user_message.split()
    key_words = [w for w in words if w.lower() not in skip_words and len(w) > 2 and not w.startswith('"')]
    
    return ' '.join(query_parts + key_words[:5]) if query_parts or key_words else user_message


def get_email_body(payload: dict) -> str:
    """Extract email body from Gmail message payload."""
    plain_texts, html_texts = [], []
    
    def extract_parts(part):
        mime_type = part.get('mimeType', '')
        if part.get('body', {}).get('data'):
            try:
                decoded = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                if decoded.strip():
                    if mime_type == 'text/plain':
                        plain_texts.append(decoded)
                    elif mime_type == 'text/html':
                        html_texts.append(decoded)
            except Exception:
                pass
        if 'parts' in part:
            for subpart in part['parts']:
                extract_parts(subpart)
    
    extract_parts(payload)
    
    if plain_texts:
        return '\n\n'.join(plain_texts)
    
    if html_texts:
        html = '\n\n'.join(html_texts)
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
        html = re.sub(r'</p>', '\n\n', html, flags=re.IGNORECASE)
        html = re.sub(r'<[^>]+>', '', html)
        html = html.replace('&nbsp;', ' ').replace('&amp;', '&')
        return '\n'.join(line.strip() for line in html.split('\n') if line.strip())
    
    return ""


def get_attachments(service, message_id: str, payload: dict) -> List[Tuple[str, bytes]]:
    """Extract all attachments from an email."""
    attachments = []
    
    def process_parts(parts):
        for part in parts:
            filename = part.get('filename', '')
            if filename:
                attachment_id = part.get('body', {}).get('attachmentId')
                if attachment_id:
                    att = service.users().messages().attachments().get(
                        userId='me', messageId=message_id, id=attachment_id
                    ).execute()
                    attachments.append((filename, base64.urlsafe_b64decode(att['data'])))
                elif part.get('body', {}).get('data'):
                    attachments.append((filename, base64.urlsafe_b64decode(part['body']['data'])))
            if 'parts' in part:
                process_parts(part['parts'])
    
    if 'parts' in payload:
        process_parts(payload['parts'])
    return attachments


def quick_gmail_search(query: str, max_results: int = 3) -> str:
    """Search Gmail and return FULL email content with caching."""
    try:
        service = get_gmail_service()
        optimized_query = extract_gmail_query(query)
        
        results = service.users().messages().list(
            userId='me', q=optimized_query, maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            return f"No emails found for: '{query}'"
        
        if 'email_cache' not in st.session_state:
            st.session_state.email_cache = {}
        
        email_contents = []
        current_search_results = []
        
        for i, msg_info in enumerate(messages, 1):
            message = service.users().messages().get(
                userId='me', id=msg_info['id'], format='full'
            ).execute()
            
            headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
            subject = headers.get('Subject', 'No Subject')
            sender = headers.get('From', 'Unknown')
            date = headers.get('Date', 'Unknown')
            
            current_search_results.append({
                'index': i, 'id': msg_info['id'], 'subject': subject, 'sender': sender
            })
            
            body = get_email_body(message['payload'])
            
            # Check for attachments
            attachment_names = []
            def find_attachments(p):
                if 'parts' in p:
                    for part in p['parts']:
                        if part.get('filename'):
                            attachment_names.append(part['filename'])
                        if 'parts' in part:
                            find_attachments(part)
            find_attachments(message['payload'])
            
            email_output = [
                f"--- EMAIL #{i} ---",
                f"**Subject:** {subject}",
                f"**From:** {sender}",
                f"**Date:** {date}"
            ]
            if attachment_names:
                email_output.append(f"**Attachments ({len(attachment_names)}):** {', '.join(attachment_names)}")
            email_output.extend(["", "**Full Content:**", body or "(No text content)", ""])
            email_contents.append("\n".join(email_output))
        
        st.session_state.email_cache = current_search_results
        return f"Found {len(messages)} email(s):\n\n" + "\n".join(email_contents)
    except Exception as e:
        return f"❌ Error: {str(e)}"


def get_email_by_index(index: int) -> str:
    """Fetch email content by its index from the last search."""
    try:
        if 'email_cache' not in st.session_state or not st.session_state.email_cache:
            return "❌ No recent search results. Please search for emails first."
        
        target = next((e for e in st.session_state.email_cache if e['index'] == index), None)
        if not target:
            return f"❌ Email #{index} not found (available: 1-{len(st.session_state.email_cache)})"
        
        st.session_state.last_viewed_email_index = index
        
        service = get_gmail_service()
        message = service.users().messages().get(
            userId='me', id=target['id'], format='full'
        ).execute()
        
        headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
        body = get_email_body(message['payload'])
        
        output = [
            f"**Email #{index}**",
            f"**Subject:** {headers.get('Subject', 'No Subject')}",
            f"**From:** {headers.get('From', 'Unknown')}",
            f"**Date:** {headers.get('Date', 'Unknown')}",
            "\n---\n",
            body or "(No text content)"
        ]
        return "\n".join(output)
    except Exception as e:
        return f"❌ Error: {str(e)}"


def analyze_attachment(email_index: int, attachment_index: int = 1) -> str:
    """Analyze attachment from a cached email."""
    try:
        if 'email_cache' not in st.session_state or not st.session_state.email_cache:
            return "❌ No recent search. Search for emails first!"
        
        target = next((e for e in st.session_state.email_cache if e['index'] == email_index), None)
        if not target:
            return f"❌ Email #{email_index} not found."
        
        service = get_gmail_service()
        message = service.users().messages().get(
            userId='me', id=target['id'], format='full'
        ).execute()
        
        all_attachments = []
        def collect(payload):
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('filename'):
                        all_attachments.append(part)
                    if 'parts' in part:
                        collect(part)
        collect(message['payload'])
        
        if not all_attachments:
            return f"❌ No attachments in Email #{email_index}."
        
        targets = all_attachments if attachment_index == 0 else (
            [all_attachments[attachment_index - 1]] if 1 <= attachment_index <= len(all_attachments) else []
        )
        if not targets:
            return f"❌ Attachment #{attachment_index} not found."
        
        results = []
        for att in targets:
            filename = att['filename']
            att_id = att['body'].get('attachmentId')
            
            if att_id:
                data = service.users().messages().attachments().get(
                    userId='me', messageId=target['id'], id=att_id
                ).execute()
                file_data = base64.urlsafe_b64decode(data['data'])
            elif att['body'].get('data'):
                file_data = base64.urlsafe_b64decode(att['body']['data'])
            else:
                results.append(f"❌ Could not download '{filename}'")
                continue
            
            text = parse_attachment(file_data, filename)
            if not text or text.startswith("[Error"):
                results.append(f"❌ Could not parse '{filename}'")
                continue
            
            clean = " ".join(text.split())[:500] + "..."
            icon = "📊" if filename.endswith(('.xls', '.xlsx')) else "📕" if filename.endswith('.pdf') else "📄"
            
            results.append(f"""
╭──────────────────────────────────────╮
│  {icon}  **{filename}**
╰──────────────────────────────────────╯
**Size:** {len(file_data)/1024:.1f} KB

**Content (first 500 chars):**
"{clean}"
""")
        
        return "\n".join(results)
    except Exception as e:
        return f"❌ Error: {str(e)}"


def get_full_email(query: str) -> str:
    """Fetch the full content of an email matching the query."""
    try:
        service = get_gmail_service()
        results = service.users().messages().list(
            userId='me', q=extract_gmail_query(query), maxResults=1
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            return f"No email found matching: '{query}'"
        
        message = service.users().messages().get(
            userId='me', id=messages[0]['id'], format='full'
        ).execute()
        
        headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
        body = get_email_body(message['payload'])
        
        output = [
            "=== FULL EMAIL ===",
            f"**Subject:** {headers.get('Subject', 'No Subject')}",
            f"**From:** {headers.get('From', 'Unknown')}",
            f"**Date:** {headers.get('Date', 'Unknown')}",
            "\n---\n",
            body or "(No text content)",
            "\n=== END EMAIL ==="
        ]
        return "\n".join(output)
    except Exception as e:
        return f"❌ Error: {str(e)}"


def check_gmail_and_learn(query: str, max_emails: int = 2, skip_attachments: bool = True) -> str:
    """Search Gmail and return email count summary."""
    try:
        service = get_gmail_service()
        optimized = extract_gmail_query(query)
        
        results = service.users().messages().list(
            userId='me', q=optimized, maxResults=max_emails
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            return f"No emails found for: '{query}'"
        
        subjects = []
        for msg_info in messages:
            message = service.users().messages().get(
                userId='me', id=msg_info['id'], format='full'
            ).execute()
            headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
            subjects.append(headers.get('Subject', 'No Subject'))
        
        subj_list = ', '.join(f"'{s}'" for s in subjects[:3])
        return f"✅ Found {len(messages)} email(s).\n📧 Subjects: {subj_list}\n💡 Use `quick_gmail_search` for full content."
    except Exception as e:
        return f"❌ Error: {str(e)}"


def fetch_email_attachments(query: str) -> str:
    """Fetch attachment info from emails matching the query."""
    try:
        service = get_gmail_service()
        results = service.users().messages().list(
            userId='me', q=extract_gmail_query(query) + " has:attachment", maxResults=2
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            return f"No emails with attachments found for: '{query}'"
        
        info = []
        for msg_info in messages:
            message = service.users().messages().get(
                userId='me', id=msg_info['id'], format='full'
            ).execute()
            headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
            subject = headers.get('Subject', 'No Subject')
            
            for filename, _ in get_attachments(service, msg_info['id'], message['payload'])[:3]:
                info.append(f"📎 {filename} (from: {subject})")
        
        return f"Found {len(info)} attachment(s):\n" + "\n".join(info) if info else "No attachments found."
    except Exception as e:
        return f"❌ Error: {str(e)}"
