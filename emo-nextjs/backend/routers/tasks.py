"""
EMO Backend - Task Router
==========================
RESTful endpoints for task management.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from services.task_service import get_task_service


router = APIRouter()


class TaskCreate(BaseModel):
    """Request model for creating a task."""
    task: str
    deadline: Optional[str] = None  # ISO datetime string


class TaskComplete(BaseModel):
    """Request model for completing a task."""
    task_number: int


class TaskResponse(BaseModel):
    """Response model for task operations."""
    success: bool
    message: str
    pending_count: Optional[int] = None


class TaskListResponse(BaseModel):
    """Response model for task list."""
    tasks: List[dict]
    count: int


@router.post("/tasks", response_model=TaskResponse)
async def create_task(task_data: TaskCreate):
    """
    Add a new task to the todo list.
    
    Request body:
        {
            "task": "Complete project documentation",
            "deadline": "2025-12-15T17:00:00"  # Optional
        }
    """
    try:
        service = get_task_service()
        new_task = service.add_task(task_data.task, task_data.deadline)
        pending = len(service.get_pending_tasks())
        
        deadline_info = ""
        if new_task.get('deadline'):
            deadline_info = f" (deadline: {new_task['deadline'][:16]})"
        
        return TaskResponse(
            success=True,
            message=f"Đã thêm task: {task_data.task}{deadline_info}",
            pending_count=pending
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks", response_model=TaskListResponse)
async def get_tasks(status: str = "pending"):
    """
    Get all tasks.
    
    Query params:
        status: "pending" (default) or "all"
    """
    try:
        service = get_task_service()
        
        if status == "all":
            tasks = service.get_all_tasks()
        else:
            tasks = service.get_pending_tasks()
        
        return TaskListResponse(
            tasks=tasks,
            count=len(tasks)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/complete", response_model=TaskResponse)
async def complete_task(task_data: TaskComplete):
    """
    Mark a task as completed.
    
    Request body:
        {
            "task_number": 1
        }
    """
    try:
        service = get_task_service()
        
        if service.complete_task_by_index(task_data.task_number):
            pending = len(service.get_pending_tasks())
            return TaskResponse(
                success=True,
                message=f"Đã hoàn thành task #{task_data.task_number}",
                pending_count=pending
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy task #{task_data.task_number}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tasks/completed")
async def delete_completed_tasks():
    """Delete all completed tasks."""
    try:
        service = get_task_service()
        service.delete_completed()
        remaining = len(service.get_pending_tasks())
        
        return TaskResponse(
            success=True,
            message="Đã xóa tất cả task đã hoàn thành",
            pending_count=remaining
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/reminders")
async def get_task_reminders():
    """Get smart reminders for upcoming and overdue tasks."""
    try:
        from services.task_service import get_smart_reminders
        reminders = get_smart_reminders()
        
        return {
            "has_reminders": bool(reminders),
            "reminders": reminders
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
