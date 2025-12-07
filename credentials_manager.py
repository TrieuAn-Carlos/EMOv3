"""
EMO2 - Credentials Manager (MVP)
================================
Simple credential storage for Gmail and Calendar accounts.
Stores OAuth tokens in JSON without encryption (MVP version).
"""

import json
import os
from typing import Optional, Dict, List, Any

ACCOUNTS_FILE = 'connected_accounts.json'


def _load_accounts() -> Dict[str, Dict[str, Any]]:
    """Load accounts from storage."""
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {'gmail': {}, 'calendar': {}}


def _save_accounts(accounts: Dict[str, Dict[str, Any]]) -> None:
    """Save accounts to storage."""
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(accounts, f, indent=2)


def store_account(
    service: str,
    email: str,
    token_data: Dict[str, Any],
    is_primary: bool = False
) -> None:
    """
    Store an account's OAuth token.
    
    Args:
        service: 'gmail' or 'calendar'
        email: User's email address
        token_data: OAuth token dictionary
        is_primary: Whether this is the primary account for this service
    """
    accounts = _load_accounts()
    
    if service not in accounts:
        accounts[service] = {}
    
    # If setting as primary, remove primary from others
    if is_primary:
        for acc_email in accounts[service]:
            accounts[service][acc_email]['primary'] = False
    
    accounts[service][email] = {
        'token': token_data,
        'primary': is_primary or len(accounts[service]) == 0  # First account is primary
    }
    
    _save_accounts(accounts)


def get_account(service: str, email: str) -> Optional[Dict[str, Any]]:
    """Get a specific account's data."""
    accounts = _load_accounts()
    return accounts.get(service, {}).get(email)


def get_primary_account(service: str) -> Optional[Dict[str, Any]]:
    """Get the primary account for a service."""
    accounts = _load_accounts()
    service_accounts = accounts.get(service, {})
    
    for email, data in service_accounts.items():
        if data.get('primary', False):
            return {'email': email, **data}
    
    # If no primary, return first account
    if service_accounts:
        email, data = next(iter(service_accounts.items()))
        return {'email': email, **data}
    
    return None


def get_all_accounts(service: str) -> List[Dict[str, Any]]:
    """Get all accounts for a service."""
    accounts = _load_accounts()
    service_accounts = accounts.get(service, {})
    
    return [
        {'email': email, **data}
        for email, data in service_accounts.items()
    ]


def remove_account(service: str, email: str) -> bool:
    """Remove an account."""
    accounts = _load_accounts()
    
    if service in accounts and email in accounts[service]:
        was_primary = accounts[service][email].get('primary', False)
        del accounts[service][email]
        
        # If removed primary, make first remaining account primary
        if was_primary and accounts[service]:
            first_email = next(iter(accounts[service]))
            accounts[service][first_email]['primary'] = True
        
        _save_accounts(accounts)
        return True
    return False


def set_primary(service: str, email: str) -> bool:
    """Set an account as primary."""
    accounts = _load_accounts()
    
    if service not in accounts or email not in accounts[service]:
        return False
    
    for acc_email in accounts[service]:
        accounts[service][acc_email]['primary'] = (acc_email == email)
    
    _save_accounts(accounts)
    return True


def is_connected(service: str) -> bool:
    """Check if any account is connected for a service."""
    accounts = _load_accounts()
    return bool(accounts.get(service, {}))
