"""
Calendar Router
Expose calendar actions via REST endpoints.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from integrations import calendar as calendar_integration

router = APIRouter()


class CreateEventRequest(BaseModel):
    summary: str
    start_time: str
    end_time: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None


class QuickAddRequest(BaseModel):
    text: str


@router.get("/events/upcoming")
async def list_upcoming(days: int = Query(7, ge=1, le=30), max_results: int = Query(10, ge=1, le=50)):
    try:
        return {"result": calendar_integration.list_upcoming_events(days=days, max_results=max_results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/search")
async def search_events(query: str, days: int = Query(30, ge=1, le=90)):
    try:
        return {"result": calendar_integration.search_events(query=query, days=days)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events/quick-add")
async def quick_add(req: QuickAddRequest):
    try:
        return {"result": calendar_integration.quick_add_event(req.text)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events/create")
async def create_event(req: CreateEventRequest):
    try:
        return {
            "result": calendar_integration.create_event(
                summary=req.summary,
                start_time=req.start_time,
                end_time=req.end_time,
                description=req.description,
                location=req.location,
            )
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
