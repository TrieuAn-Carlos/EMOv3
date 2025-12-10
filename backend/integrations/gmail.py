"""
EMO Backend - Gmail Integration
================================
Full Gmail OAuth and email functions - no Streamlit dependencies.
"""

import os
import re
import json
import base64
from typing import List, Tuple, Optional
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
BASE_DIR = Path(__file__).parent.parent
CREDENTIALS_FILE = BASE_DIR / 'credentials.json'
TOKEN_FILE = BASE_DIR / 'data' / 'gmail_token.json'

# In-memory cache (replaces st.session_state)
_gmail_service = None
_email_cache: List[dict] = []


def authenticate_gmail():
    """Authenticate with Gmail API using OAuth 2.0."""
    global _gmail_service
    
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
                raise FileNotFoundError(f"'{CREDENTIALS_FILE}' not found. Please add OAuth credentials.")
            
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save token
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
    
    _gmail_service = build('gmail', 'v1', credentials=creds)
    return _gmail_service


def get_gmail_service():
    """Get or create Gmail service instance."""
    global _gmail_service
    if _gmail_service is None:
        _gmail_service = authenticate_gmail()
    return _gmail_service


def disconnect_gmail():
    """Disconnect Gmail by clearing service and token."""
    global _gmail_service, _email_cache
    _gmail_service = None
    _email_cache = []
    
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
    return True


def is_gmail_connected() -> bool:
    """Check if Gmail is connected."""
    return TOKEN_FILE.exists()


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


def quick_gmail_search(query: str, max_results: int = 5) -> str:
    """
    Search Gmail and return LIGHTWEIGHT preview (no body content).
    Uses Gmail Batch API for maximum speed.
    
    Returns a numbered list with sender, subject, and date ONLY.
    Use get_email_by_index() to fetch full content for a specific email.
    """
    global _email_cache
    
    try:
        service = get_gmail_service()
        optimized_query = extract_gmail_query(query)
        
        # Step 1: Get message IDs (fast)
        results = service.users().messages().list(
            userId='me', 
            q=optimized_query, 
            maxResults=max_results,
            fields='messages(id)'  # Only get IDs, not full metadata
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            return f"No emails found for: '{query}'"
        
        # Step 2: Batch fetch metadata (single HTTP request!)
        from googleapiclient.http import BatchHttpRequest
        
        _email_cache = []
        email_data = []
        
        def callback(request_id, response, exception):
            if exception:
                return
            
            index = int(request_id)
            headers = {h['name']: h['value'] for h in response.get('payload', {}).get('headers', [])}
            subject = headers.get('Subject', 'No Subject')
            sender = headers.get('From', 'Unknown')
            date = headers.get('Date', 'Unknown')
            
            sender_display = sender.split('<')[0].strip().strip('"') if '<' in sender else sender
            date_display = date.split(',')[-1].strip()[:12] if date else 'Unknown'
            
            email_data.append({
                'index': index,
                'id': response['id'],
                'subject': subject,
                'sender': sender,
                'sender_display': sender_display,
                'date': date,
                'date_display': date_display
            })
        
        # Create batch request
        batch = service.new_batch_http_request(callback=callback)
        
        for i, msg_info in enumerate(messages, 1):
            batch.add(
                service.users().messages().get(
                    userId='me',
                    id=msg_info['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date'],
                    fields='id,payload(headers)'  # Only needed fields
                ),
                request_id=str(i)
            )
        
        # Execute all requests in single HTTP call
        batch.execute()
        
        # Sort by index and build output
        email_data.sort(key=lambda x: x['index'])
        
        for data in email_data:
            _email_cache.append({
                'index': data['index'],
                'id': data['id'],
                'subject': data['subject'],
                'sender': data['sender'],
                'date': data['date']
            })
        
        # Build compact, clean email list
        email_previews = []
        for d in email_data:
            # Truncate long subjects
            subject = d['subject']
            if len(subject) > 50:
                subject = subject[:47] + "..."
            
            # Truncate long sender names
            sender = d['sender_display']
            if len(sender) > 25:
                sender = sender[:22] + "..."
            
            email_previews.append(
                f"**[{d['index']}]** `{sender}` · _{subject}_ · `{d['date_display']}`"
            )
        
        header = f"📬 **Found {len(messages)} email(s)**\n\n"
        return header + "\n".join(email_previews)
    except Exception as e:
        if "invalid_grant" in str(e).lower():
            disconnect_gmail()
            return "Gmail token expired. Please reconnect Gmail."
        return f"Error: {str(e)}"


def get_email_by_index(index: int) -> str:
    """
    Fetch FULL email content by index from the last search.
    Optimized with field filtering to reduce data transfer.
    
    This is the second step in the 2-step retrieval:
    1. search_gmail() → lightweight list with indices
    2. get_email_by_index(n) → full content for email #n
    """
    global _email_cache
    
    try:
        if not _email_cache:
            return "No recent search results. Please search for emails first."
        
        target = next((e for e in _email_cache if e['index'] == index), None)
        if not target:
            return f"Email #{index} not found (available: 1-{len(_email_cache)})"
        
        service = get_gmail_service()
        
        # Only fetch needed fields to reduce data transfer
        message = service.users().messages().get(
            userId='me',
            id=target['id'],
            format='full',
            fields='id,payload(headers,parts,body,mimeType)'  # Only needed fields
        ).execute()
        
        headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
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
        
        # Truncate long body for preview
        body_preview = body or "(No text content)"
        if len(body_preview) > 500:
            body_preview = body_preview[:497] + "..."
        
        # Build compact, clean output
        output = [
            f"### 📧 Email #{index}",
            "",
            f"**From:** {headers.get('From', 'Unknown')}",
            f"**Subject:** {headers.get('Subject', 'No Subject')}",
            f"**Date:** {headers.get('Date', 'Unknown')}"
        ]
        
        if attachment_names:
            attachments_str = ", ".join(f"`{name}`" for name in attachment_names[:3])
            if len(attachment_names) > 3:
                attachments_str += f" (+{len(attachment_names)-3} more)"
            output.append(f"**📎 Attachments:** {attachments_str}")
        
        output.extend([
            "",
            "**Content:**",
            "```",
            body_preview,
            "```"
        ])
        
        return "\n".join(output)
    except Exception as e:
        return f"Error: {str(e)}"


def analyze_attachment(email_index: int, attachment_index: int = 1) -> str:
    """Analyze attachment from a cached email."""
    global _email_cache
    
    try:
        if not _email_cache:
            return "❌ No recent search. Search for emails first!"
        
        target = next((e for e in _email_cache if e['index'] == email_index), None)
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
            
            # Try to parse (simplified - just show first 500 chars)
            try:
                text = file_data.decode('utf-8', errors='ignore')[:500]
            except:
                text = f"[Binary file: {len(file_data)} bytes]"
            
            icon = "📊" if filename.endswith(('.xls', '.xlsx')) else "📕" if filename.endswith('.pdf') else "📄"
            
            results.append(f"""
╭──────────────────────────────────────╮
│  {icon}  **{filename}**
╰──────────────────────────────────────╯
**Size:** {len(file_data)/1024:.1f} KB

**Content preview:**
{text}...
""")
        
        return "\n".join(results)
    except Exception as e:
        return f"❌ Error: {str(e)}"
