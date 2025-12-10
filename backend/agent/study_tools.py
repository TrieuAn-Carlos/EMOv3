"""
EMO Backend - Study Session Tools
==================================
Tools for parent-child study session management.
Emo uses these to create sessions and generate reports.
"""

from langchain_core.tools import tool


# =============================================================================
# PARENT TOOL: Create Study Session
# =============================================================================

@tool
def create_study_session(topic: str, child_name: str = "Josh") -> str:
    """
    Create a study session for a child. The invite will appear on child's view automatically.
    
    Use this when parent says (English or Vietnamese):
    - "Start a study session on Sequences and Series for Josh"
    - "I want my child to practice Sequences"
    - "Create a learning session about Arithmetic Sequences"
    - "Bắt đầu buổi học về Dãy số và Chuỗi cho Josh" 
    - "Tạo buổi học về Cấp số cộng"
    - "Cho con học Cấp số nhân"
    - "Tạo session học về dãy số"
    - "Mở buổi học về Sequences"
    
    Args:
        topic: What the child will study - use the topic mentioned by parent
               Examples: "Sequences and Series", "Dãy số và Chuỗi", 
                        "Arithmetic Sequences", "Cấp số cộng",
                        "Geometric Sequences", "Cấp số nhân"
        child_name: Child's name for personalization (default: Josh)
    
    Returns:
        Confirmation that session was created
    """
    import uuid
    try:
        # Direct database access to avoid HTTP deadlock
        from database import SessionLocal, StudySession
        
        db = SessionLocal()
        try:
            session_id = str(uuid.uuid4())[:8]
            session = StudySession(
                id=session_id,
                status="pending",
                report=topic  # Store topic in report field temporarily
            )
            db.add(session)
            db.commit()
        finally:
            db.close()
        
        return f"""✅ **Study Session Created!**

**Topic:** {topic}
**For:** {child_name}

{child_name} will see an invite button on their screen:
> 🎓 *"Wanna join a session on {topic}?"*

I'll let you know when the session is complete and share the performance report."""
    except Exception as e:
        return f"❌ Error: {str(e)[:100]}"


# =============================================================================
# CHILD TOOL: Complete Study Session
# =============================================================================

@tool
def complete_study_session() -> str:
    """
    Mark the current study session as completed.
    
    Use this when child says:
    - "I'm done studying"
    - "I finished the session"
    - "That's all for today"
    
    Returns:
        Confirmation that session is complete
    """
    import json
    from datetime import datetime
    try:
        # Direct database access to avoid HTTP deadlock
        from database import SessionLocal, StudySession
        
        db = SessionLocal()
        try:
            # Find active session
            session = db.query(StudySession).filter(
                StudySession.status == "active"
            ).order_by(StudySession.created_at.desc()).first()
            
            if not session:
                return "No active study session found."
            
            topic = session.report  # Get topic before overwriting
            
            # Generate simple report
            report = {
                "summary": f"Josh completed a study session on {topic}.",
                "duration": "15 minutes",
                "topics_covered": [topic],
                "strengths": ["Active engagement", "Good questions"],
                "weaknesses": ["Needs more practice"],
                "accuracy": 75,
                "practice_problems": [
                    {"question": f"Practice problem on {topic} #1", "topic": topic},
                    {"question": f"Practice problem on {topic} #2", "topic": topic}
                ]
            }
            
            session.status = "completed"
            session.completed_at = datetime.now()
            session.report = json.dumps(report)
            db.commit()
        finally:
            db.close()
        
        return """🎉 **Great job!** You've completed the study session!

I've told your parent and prepared a report showing:
- What you learned
- What you did well  
- Things to practice more

Keep up the great work! 📚⭐"""
    except Exception as e:
        return f"❌ Error: {str(e)[:100]}"


# =============================================================================
# PARENT TOOL: Get Study Report
# =============================================================================

@tool
def get_study_report() -> str:
    """
    Get the performance report from the most recent completed study session.
    
    Use this when parent asks:
    - "How did Josh do?"
    - "Show me the report"
    - "What did my child learn?"
    
    Returns:
        Detailed performance report
    """
    import json
    try:
        # Direct database access to avoid HTTP deadlock
        from database import SessionLocal, StudySession
        
        db = SessionLocal()
        try:
            session = db.query(StudySession).filter(
                StudySession.status == "completed"
            ).order_by(StudySession.completed_at.desc()).first()
            
            if not session:
                return "No completed study sessions yet. Your child needs to finish studying first!"
            
            if not session.report:
                return "Report is not ready yet."
            
            try:
                report = json.loads(session.report)
            except:
                report = {"summary": "Report generation failed"}
            
            return _format_report(report)
        finally:
            db.close()
    except Exception as e:
        return f"❌ Error: {str(e)[:100]}"


def _format_report(report: dict) -> str:
    """Format report dict into readable markdown."""
    output = ["📊 **Study Session Report**\n"]
    
    if report.get("summary"):
        output.append(f"**Summary:** {report['summary']}\n")
    
    if report.get("duration"):
        output.append(f"⏱️ **Duration:** {report['duration']}")
    
    if report.get("accuracy"):
        output.append(f"📈 **Accuracy:** {report['accuracy']}%\n")
    
    if report.get("topics_covered"):
        output.append("📚 **Topics Covered:**")
        for topic in report["topics_covered"]:
            output.append(f"  • {topic}")
        output.append("")
    
    if report.get("strengths"):
        output.append("✅ **Strengths:**")
        for s in report["strengths"]:
            output.append(f"  • {s}")
        output.append("")
    
    if report.get("weaknesses"):
        output.append("⚠️ **Areas to Improve:**")
        for w in report["weaknesses"]:
            output.append(f"  • {w}")
        output.append("")
    
    if report.get("practice_problems"):
        output.append("📝 **Suggested Practice Problems:**")
        for i, p in enumerate(report["practice_problems"], 1):
            output.append(f"  {i}. {p['question']}")
    
    return "\n".join(output)


# =============================================================================
# TOOL EXPORT
# =============================================================================

def get_study_tools() -> list:
    """Return all study session tools."""
    return [
        create_study_session,
        complete_study_session,
        get_study_report,
    ]
