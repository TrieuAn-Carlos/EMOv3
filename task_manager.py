"""
EMO2 - Task Manager
===================
Task management with deadline support and smart reminders.
Persists tasks to a local JSON file.
"""

import os
import json
import uuid
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import streamlit as st

TODO_FILE = 'todo.json'


class TaskManager:
    """Task manager with deadline support and smart reminders."""
    
    def __init__(self, filepath: str = TODO_FILE):
        self.filepath = filepath
        self.tasks = self._load_tasks()
    
    def _load_tasks(self) -> List[Dict]:
        """Load tasks from JSON file."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []
    
    def _save_tasks(self):
        """Save tasks to JSON file."""
        with open(self.filepath, 'w') as f:
            json.dump(self.tasks, f, indent=2)
    
    def _parse_deadline(self, task_text: str) -> Optional[datetime]:
        """
        Extract deadline from task text. Language-agnostic - focuses on time patterns.
        Supports: "11pm", "at 3:30 pm", "Dec 6, 2025 at 2 PM", "tomorrow 5pm", "11h30"
        """
        text_lower = task_text.lower()
        now = datetime.now()
        target_date = now.date()
        
        # Parse date from text
        month_names = {
            'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
            'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6,
            'jul': 7, 'july': 7, 'aug': 8, 'august': 8, 'sep': 9, 'september': 9,
            'oct': 10, 'october': 10, 'nov': 11, 'november': 11, 'dec': 12, 'december': 12
        }
        
        date_pattern = r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:,?\s*(\d{4}))?'
        date_match = re.search(date_pattern, text_lower)
        if date_match:
            month = month_names.get(date_match.group(1)[:3], now.month)
            day = int(date_match.group(2))
            year = int(date_match.group(3)) if date_match.group(3) else now.year
            try:
                from datetime import date
                target_date = date(year, month, day)
            except:
                pass
        
        # ISO date pattern
        iso_date = re.search(r'(\d{4})-(\d{2})-(\d{2})', task_text)
        if iso_date:
            try:
                from datetime import date
                target_date = date(int(iso_date.group(1)), int(iso_date.group(2)), int(iso_date.group(3)))
            except:
                pass
        
        # Relative dates
        if 'tomorrow' in text_lower or 'ngày mai' in text_lower:
            target_date = (now + timedelta(days=1)).date()
        
        # Parse time
        hour, minute = None, 0
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)?',
            r'(?:at|by|@|lúc|vào)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.|giờ|h)?',
            r'(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)',
            r'(\d{1,2})h(\d{2})?',
            r'from\s*(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)?',
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text_lower)
            if match:
                groups = match.groups()
                hour = int(groups[0])
                
                if len(groups) > 1 and groups[1] and groups[1].isdigit():
                    minute = int(groups[1])
                
                ampm = None
                for g in groups:
                    if g and isinstance(g, str) and g.lower().replace('.', '') in ['am', 'pm']:
                        ampm = g.lower().replace('.', '')
                        break
                
                if ampm == 'pm' and hour != 12:
                    hour += 12
                elif ampm == 'am' and hour == 12:
                    hour = 0
                elif ampm is None and hour <= 12 and hour >= 1:
                    if hour < 7:
                        hour += 12
                break
        
        if hour is not None:
            try:
                deadline = datetime.combine(target_date, datetime.min.time().replace(hour=hour, minute=minute))
                if deadline < now and not date_match and not iso_date:
                    deadline += timedelta(days=1)
                return deadline
            except:
                pass
        
        return None
    
    def add_task(self, task: str) -> Dict:
        """Add a new task with optional deadline detection."""
        deadline = self._parse_deadline(task)
        new_task = {
            'id': str(uuid.uuid4()),
            'task': task,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'deadline': deadline.isoformat() if deadline else None
        }
        self.tasks.append(new_task)
        self._save_tasks()
        return new_task
    
    def get_pending_tasks(self) -> List[Dict]:
        """Return all pending tasks."""
        return [t for t in self.tasks if t['status'] == 'pending']
    
    def get_all_tasks(self) -> List[Dict]:
        """Return all tasks."""
        return self.tasks
    
    def get_upcoming_deadlines(self, within_minutes: int = 60) -> List[Dict]:
        """Get tasks with deadlines coming up within specified minutes."""
        now = datetime.now()
        upcoming = []
        
        for task in self.get_pending_tasks():
            if task.get('deadline'):
                try:
                    deadline = datetime.fromisoformat(task['deadline'])
                    minutes_until = (deadline - now).total_seconds() / 60
                    
                    if 0 < minutes_until <= within_minutes:
                        upcoming.append({
                            **task,
                            'minutes_until': int(minutes_until),
                            'deadline_dt': deadline
                        })
                except:
                    pass
        
        upcoming.sort(key=lambda x: x['deadline_dt'])
        return upcoming
    
    def get_overdue_tasks(self) -> List[Dict]:
        """Get tasks that are past their deadline."""
        now = datetime.now()
        overdue = []
        
        for task in self.get_pending_tasks():
            if task.get('deadline'):
                try:
                    deadline = datetime.fromisoformat(task['deadline'])
                    if deadline < now:
                        minutes_overdue = int((now - deadline).total_seconds() / 60)
                        overdue.append({
                            **task,
                            'minutes_overdue': minutes_overdue,
                            'deadline_dt': deadline
                        })
                except:
                    pass
        
        return overdue
    
    def complete_task_by_index(self, index: int) -> bool:
        """Mark a task as done by its 1-based index in pending tasks."""
        pending = self.get_pending_tasks()
        if 1 <= index <= len(pending):
            task_id = pending[index - 1]['id']
            return self.complete_task_by_id(task_id)
        return False
    
    def complete_task_by_id(self, task_id: str) -> bool:
        """Mark a task as done by its ID."""
        for task in self.tasks:
            if task['id'] == task_id:
                task['status'] = 'done'
                self._save_tasks()
                return True
        return False
    
    def delete_completed(self):
        """Remove all completed tasks."""
        self.tasks = [t for t in self.tasks if t['status'] != 'done']
        self._save_tasks()
    
    def reload(self):
        """Reload tasks from file and backfill missing deadlines."""
        self.tasks = self._load_tasks()
        self._backfill_deadlines()
    
    def _backfill_deadlines(self):
        """Parse deadlines for existing tasks that don't have them."""
        updated = False
        for task in self.tasks:
            if task.get('deadline') is None and task.get('status') == 'pending':
                deadline = self._parse_deadline(task['task'])
                if deadline:
                    task['deadline'] = deadline.isoformat()
                    updated = True
        if updated:
            self._save_tasks()


def get_task_manager() -> TaskManager:
    """Get or create TaskManager instance."""
    st.session_state.task_manager = TaskManager()
    return st.session_state.task_manager


def get_smart_reminders() -> str:
    """Check for upcoming deadlines and overdue tasks."""
    manager = get_task_manager()
    reminders = []
    
    for task in manager.get_overdue_tasks():
        mins = task['minutes_overdue']
        time_str = f"{mins} minutes ago" if mins < 60 else f"{mins // 60} hour(s) ago"
        reminders.append(f"OVERDUE ({time_str}): {task['task']}")
    
    for task in manager.get_upcoming_deadlines(within_minutes=120):
        mins = task['minutes_until']
        deadline_time = task['deadline_dt'].strftime("%I:%M %p").lstrip('0')
        urgency = "URGENT" if mins <= 15 else "SOON" if mins <= 30 else "UPCOMING"
        
        if mins < 60:
            time_str = f"in {mins} min"
        else:
            hours, remaining = mins // 60, mins % 60
            time_str = f"in {hours}h {remaining}m" if remaining else f"in {hours} hour(s)"
        
        reminders.append(f"{urgency} ({time_str}, at {deadline_time}): {task['task']}")
    
    return "[DEADLINE ALERTS]\n" + "\n".join(reminders) if reminders else ""


# Tool functions for Gemini

def add_todo(task: str) -> str:
    """Add a new task to the to-do list."""
    manager = get_task_manager()
    manager.add_task(task)
    pending_count = len(manager.get_pending_tasks())
    st.session_state.todo_changed = True
    return f"✅ Added task: '{task}'\n📋 You now have {pending_count} pending task(s)."


def get_todos() -> str:
    """Get the list of current pending tasks."""
    manager = get_task_manager()
    pending = manager.get_pending_tasks()
    
    if not pending:
        return "📋 Your to-do list is empty. No pending tasks!"
    
    task_lines = ["📋 **Current To-Do List:**"]
    for i, task in enumerate(pending, 1):
        created = task.get('created_at', 'Unknown')[:10]
        task_lines.append(f"{i}. {task['task']} (added: {created})")
    
    task_lines.append(f"\n**Total: {len(pending)} pending task(s)**")
    return "\n".join(task_lines)


def complete_todo(task_index: int) -> str:
    """Mark a task as done based on its index (1-based)."""
    manager = get_task_manager()
    pending = manager.get_pending_tasks()
    
    if not pending:
        return "📋 Your to-do list is empty. Nothing to complete!"
    
    if task_index < 1 or task_index > len(pending):
        return f"❌ Invalid task index. Please choose between 1 and {len(pending)}."
    
    task_name = pending[task_index - 1]['task']
    success = manager.complete_task_by_index(task_index)
    
    if success:
        remaining = len(manager.get_pending_tasks())
        st.session_state.todo_changed = True
        return f"✅ Completed: '{task_name}'\n📋 {remaining} task(s) remaining."
    return f"❌ Failed to complete task at index {task_index}."
