"""
Gmail Connection Test Script
Run this to check if your Gmail API connection is working properly.
"""

import os
import sys

# Add colors for console output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def log_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} {msg}")

def log_success(msg):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} {msg}")

def log_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {msg}")

def log_warning(msg):
    print(f"{Colors.YELLOW}[WARNING]{Colors.RESET} {msg}")

def test_gmail_connection():
    """Test Gmail API connection step by step."""
    
    print(f"\n{Colors.BOLD}{'='*60}")
    print("       Gmail Connection Test")
    print(f"{'='*60}{Colors.RESET}\n")
    
    # Step 1: Check credentials.json
    log_info("Step 1: Checking credentials.json...")
    if os.path.exists('credentials.json'):
        log_success("credentials.json found!")
    else:
        log_error("credentials.json NOT FOUND!")
        log_warning("Please download credentials.json from Google Cloud Console")
        log_warning("Instructions: https://developers.google.com/gmail/api/quickstart/python")
        return False
    
    # Step 2: Check token.json
    log_info("Step 2: Checking token.json...")
    if os.path.exists('token.json'):
        log_success("token.json found (previous authentication exists)")
    else:
        log_warning("token.json not found - will need to authenticate")
    
    # Step 3: Try to import required libraries
    log_info("Step 3: Checking required libraries...")
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        log_success("All Google API libraries imported successfully!")
    except ImportError as e:
        log_error(f"Missing library: {e}")
        log_warning("Run: pip install google-auth-oauthlib google-api-python-client")
        return False
    
    # Step 4: Test authentication
    log_info("Step 4: Testing Gmail authentication...")
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    creds = None
    
    try:
        if os.path.exists('token.json'):
            log_info("  Loading credentials from token.json...")
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            
            if creds and creds.valid:
                log_success("  Credentials loaded and valid!")
            elif creds and creds.expired and creds.refresh_token:
                log_warning("  Credentials expired, attempting refresh...")
                try:
                    creds.refresh(Request())
                    log_success("  Credentials refreshed successfully!")
                    # Save refreshed credentials
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())
                    log_info("  Updated token.json with refreshed credentials")
                except Exception as e:
                    log_error(f"  Failed to refresh credentials: {e}")
                    log_warning("  Deleting old token.json and re-authenticating...")
                    os.remove('token.json')
                    creds = None
            else:
                log_warning("  Credentials invalid, need to re-authenticate")
                creds = None
        
        if not creds or not creds.valid:
            log_info("  Starting OAuth flow (browser will open)...")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
            # Save credentials
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
            log_success("  New credentials saved to token.json!")
    
    except Exception as e:
        log_error(f"Authentication failed: {e}")
        return False
    
    # Step 5: Build Gmail service and test connection
    log_info("Step 5: Building Gmail service...")
    try:
        service = build('gmail', 'v1', credentials=creds)
        log_success("Gmail service built successfully!")
    except Exception as e:
        log_error(f"Failed to build Gmail service: {e}")
        return False
    
    # Step 6: Test API call - get user profile
    log_info("Step 6: Testing API call (fetching user profile)...")
    try:
        profile = service.users().getProfile(userId='me').execute()
        email = profile.get('emailAddress', 'Unknown')
        total_messages = profile.get('messagesTotal', 0)
        log_success(f"Connected to Gmail account: {email}")
        log_info(f"  Total messages in account: {total_messages}")
    except HttpError as e:
        log_error(f"API call failed: {e}")
        if e.resp.status == 403:
            log_warning("Permission denied - check if Gmail API is enabled in Google Cloud Console")
        elif e.resp.status == 401:
            log_warning("Unauthorized - try deleting token.json and re-authenticating")
        return False
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        return False
    
    # Step 7: Try to fetch recent emails
    log_info("Step 7: Testing email fetch (last 5 emails)...")
    try:
        results = service.users().messages().list(userId='me', maxResults=5).execute()
        messages = results.get('messages', [])
        
        if messages:
            log_success(f"Successfully fetched {len(messages)} emails!")
            for i, msg in enumerate(messages, 1):
                log_info(f"  Email {i}: ID = {msg['id']}")
        else:
            log_warning("No emails found in inbox (but connection works)")
    except Exception as e:
        log_error(f"Failed to fetch emails: {e}")
        return False
    
    # All tests passed
    print(f"\n{Colors.GREEN}{Colors.BOLD}{'='*60}")
    print("  ALL TESTS PASSED! Gmail connection is working!")
    print(f"{'='*60}{Colors.RESET}\n")
    
    return True

if __name__ == "__main__":
    success = test_gmail_connection()
    sys.exit(0 if success else 1)
