"""
EMO Backend - Task Service
===========================
Task management with deadline support and smart reminders.
FastAPI-compatible version (no Streamlit dependency).
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from core.config import TODO_FILE


class TaskService:
    """Task manager with deadline support."""
    
    def __init__(self, filepath: Path = TODO_FILE):
        self.filepath = filepath
        self.tasks = self._load_tasks()
    
    def _load_tasks(self) -> List[Dict]:
        """Load tasks from JSON file."""
        if self.filepath.exists():
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []
    
    def _save_tasks(self):
        """Save tasks to JSON file."""
        self.filepath.parent.mkdir(exist_ok=True)
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, indent=2, ensure_ascii=False)
    
    def add_task(self, task: str, deadline_iso: str = None) -> Dict:
        """Add a new task with optional deadline (ISO format)."""
        deadline = None
        if deadline_iso:
            try:
                deadline = datetime.fromisoformat(deadline_iso)
            except ValueError:
                pass
        
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
                task['completed_at'] = datetime.now().isoformat()
                self._save_tasks()
                return True
        return False
    
    def delete_completed(self):
        """Remove all completed tasks."""
        self.tasks = [t for t in self.tasks if t['status'] != 'done']
        self._save_tasks()
    
    def reload(self):
        """Reload tasks from file."""
        self.tasks = self._load_tasks()


def get_smart_reminders() -> str:
    """Check for upcoming deadlines and overdue tasks."""
    manager = TaskService()
    reminders = []
    
    # Overdue tasks
    for task in manager.get_overdue_tasks():
        mins = task['minutes_overdue']
        time_str = f"{mins} phút trước" if mins < 60 else f"{mins // 60} giờ trước"
        reminders.append(f"⚠️ QUÁ HẠN ({time_str}): {task['task']}")
    
    # Upcoming deadlines
    for task in manager.get_upcoming_deadlines(within_minutes=120):
        mins = task['minutes_until']
        deadline_time = task['deadline_dt'].strftime("%H:%M")
        urgency = "🔴 KHẨN CẤP" if mins <= 15 else "🟡 SẮP TỚI" if mins <= 30 else "🟢 SẮP ĐẾN"
        
        if mins < 60:
            time_str = f"còn {mins} phút"
        else:
            hours, remaining = mins // 60, mins % 60
            time_str = f"còn {hours}h {remaining}m" if remaining else f"còn {hours} giờ"
        
        reminders.append(f"{urgency} ({time_str}, lúc {deadline_time}): {task['task']}")
    
    return "[NHẮC NHỞ DEADLINE]\n" + "\n".join(reminders) if reminders else ""


# Singleton instance
_task_service: Optional[TaskService] = None

def get_task_service() -> TaskService:
    """Get singleton TaskService instance."""
    global _task_service
    if _task_service is None:
        _task_service = TaskService()
    return _task_service
