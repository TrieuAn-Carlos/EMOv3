"""
SocratiQ - Quiz Generation Agent
================================
LangGraph-powered agent for generating educational quizzes from PDF content.
"""

import os
import json
import base64
from io import BytesIO
from typing import Optional, Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from services.document_service import get_page_content, search_content


# =============================================================================
# QUIZ SCHEMA
# =============================================================================

class QuizQuestion(BaseModel):
    """Schema for a single quiz question."""
    question: str = Field(description="The quiz question")
    options: List[str] = Field(description="List of 4 answer options (A, B, C, D)")
    correct_answer: str = Field(description="The correct option letter (A, B, C, or D)")
    explanation: str = Field(description="Brief explanation of why the answer is correct")


class Quiz(BaseModel):
    """Schema for a complete quiz."""
    title: str = Field(description="Quiz title based on content")
    difficulty: str = Field(description="Quiz difficulty: Beginner, Intermediate, or Advanced")
    questions: List[QuizQuestion] = Field(description="List of quiz questions")


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SOCRATIQ_SYSTEM_PROMPT = """You are SocratiQ, an educational AI that generates high-quality quizzes to help students learn.

Your task is to generate a quiz based STRICTLY on the provided context. Follow these rules:

1. **Accuracy**: Only use information explicitly stated in the context. Never make up facts.
2. **Clarity**: Write clear, unambiguous questions with one correct answer.
3. **Difficulty Levels**:
   - Beginner: Basic recall, simple definitions, direct facts
   - Intermediate: Understanding relationships, applying concepts
   - Advanced: Analysis, synthesis, critical thinking

4. **Question Types**: Mix different types:
   - Factual recall
   - Conceptual understanding
   - Application scenarios
   - Cause and effect

5. **Options**: Provide 4 plausible options (A, B, C, D). Wrong options should be reasonable distractors.

6. **Explanations**: Briefly explain why the correct answer is right, referencing the source material.

Generate {num_questions} questions at {difficulty} difficulty level.
"""


# =============================================================================
# QUIZ GENERATOR
# =============================================================================

_llm = None


def get_llm():
    """Get or create LLM instance."""
    global _llm
    if _llm is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        
        _llm = ChatGoogleGenerativeAI(
            model="gemma-3-27b-it",
            google_api_key=api_key,
            temperature=0.5,
        )
    return _llm


def generate_quiz(
    doc_id: str,
    page_number: Optional[int] = None,
    context: Optional[str] = None,
    difficulty: str = "Beginner",
    num_questions: int = 5
) -> Dict[str, Any]:
    """
    Generate a quiz from document content.
    
    Args:
        doc_id: Document ID
        page_number: Specific page to quiz on (optional)
        context: Direct text context (for highlight mode)
        difficulty: Beginner, Intermediate, or Advanced
        num_questions: Number of questions to generate
        
    Returns:
        Quiz dict with title, difficulty, and questions
    """
    # Get content
    if context:
        # Highlight mode: use provided context
        content = context
    elif page_number:
        # Page mode: get page content from ChromaDB
        content = get_page_content(doc_id, page_number)
        if not content:
            raise ValueError(f"No content found for page {page_number}")
    else:
        raise ValueError("Either page_number or context must be provided")
    
    # Validate difficulty
    if difficulty not in ["Beginner", "Intermediate", "Advanced"]:
        difficulty = "Beginner"
    
    # Limit questions
    num_questions = min(max(num_questions, 1), 10)
    
    # Create prompt - Gemma doesn't support system prompts, use single human message
    prompt_text = f"""Bạn là SocratiQ, một AI giáo dục. Tạo quiz dựa trên nội dung sau.

**QUAN TRỌNG: Trả lời 100% bằng tiếng Việt!**
- Chỉ giữ tiếng Anh cho: thuật ngữ chuyên môn, trích dẫn từ tài liệu gốc, hoặc nếu đây là bài thi tiếng Anh
- Câu hỏi, đáp án, giải thích đều phải bằng tiếng Việt

**Độ khó: {difficulty}**
- Beginner (Dễ): Ghi nhớ đơn giản, định nghĩa (nhiều True/False hơn)
- Intermediate (Trung bình): Hiểu và áp dụng (mix cả hai loại)
- Advanced (Khó): Phân tích, tư duy phản biện (nhiều Multiple Choice hơn)

**Quy tắc định dạng:**
- Dùng **bold** để nhấn mạnh
- Dùng *italic* cho thuật ngữ
- Dùng ~~gạch ngang~~ cho ví dụ sai
- Dùng LaTeX cho công thức: $E = mc^2$ (inline) hoặc $$\\sum_{{i=1}}^n$$ (block)
- Phân số dùng $\\frac{{a}}{{b}}$ VÍ DỤ: $\\frac{{1}}{{2}}$, $\\frac{{3}}{{4}}$

Nội dung:
---
{content}
---

Tạo {num_questions} câu hỏi. Trộn loại câu hỏi (trắc nghiệm và đúng/sai).

Trả về CHỈ JSON hợp lệ (không có markdown code blocks):
{{
    "title": "Tiêu đề quiz bằng tiếng Việt",
    "difficulty": "{difficulty}",
    "questions": [
        {{
            "type": "multiple_choice",
            "question": "Câu hỏi bằng tiếng Việt với **in đậm** hoặc $công thức$?",
            "options": ["A. Đáp án 1", "B. Đáp án 2", "C. Đáp án 3", "D. Đáp án 4"],
            "correct_answer": "A",
            "explanation": "Giải thích bằng tiếng Việt"
        }},
        {{
            "type": "true_false",
            "question": "Phát biểu cần đánh giá?",
            "options": ["Đúng", "Sai"],
            "correct_answer": "Đúng",
            "explanation": "Lý do đúng/sai"
        }}
    ]
}}"""
    
    # Generate using HumanMessage (no system prompt for Gemma)
    from langchain_core.messages import HumanMessage
    
    llm = get_llm()
    message = HumanMessage(content=prompt_text)
    response = llm.invoke([message])
    
    # Parse response
    response_text = response.content
    
    # Clean up response (remove markdown if present)
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]
    
    try:
        quiz_data = json.loads(response_text.strip())
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parse error: {e}")
        print(f"Response was: {response_text[:500]}")
        # Return a basic structure
        quiz_data = {
            "title": "Quiz",
            "difficulty": difficulty,
            "questions": [],
            "error": "Failed to parse quiz response"
        }
    
    # Add metadata
    quiz_data["doc_id"] = doc_id
    quiz_data["page_number"] = page_number
    quiz_data["source"] = "highlight" if context else "page"
    
    return quiz_data


def generate_quiz_for_search(
    doc_id: str,
    query: str,
    difficulty: str = "Beginner",
    num_questions: int = 5
) -> Dict[str, Any]:
    """
    Generate a quiz based on semantic search results.
    
    Args:
        doc_id: Document ID
        query: Search query to find relevant content
        difficulty: Quiz difficulty
        num_questions: Number of questions
        
    Returns:
        Quiz dict
    """
    # Search for relevant content
    results = search_content(doc_id, query, n_results=3)
    
    if not results:
        raise ValueError(f"No content found matching query: {query}")
    
    # Combine results into context
    context_parts = []
    for r in results:
        context_parts.append(f"[Page {r['page_number']}]\n{r['text']}")
    
    combined_context = "\n\n---\n\n".join(context_parts)
    
    return generate_quiz(
        doc_id=doc_id,
        context=combined_context,
        difficulty=difficulty,
        num_questions=num_questions
    )


# =============================================================================
# VISION-BASED QUIZ GENERATOR
# =============================================================================

VISION_QUIZ_PROMPT = """Bạn là SocratiQ, một AI giáo dục. Nhìn vào hình ảnh trang PDF này và tạo quiz.

**QUAN TRỌNG: Trả lời 100% bằng tiếng Việt!**
- Chỉ giữ tiếng Anh cho: thuật ngữ chuyên môn, trích dẫn từ tài liệu gốc, hoặc nếu đây là bài thi tiếng Anh
- Câu hỏi, đáp án, giải thích đều phải bằng tiếng Việt

**Độ khó: {difficulty}**
- Beginner (Dễ): Ghi nhớ đơn giản, định nghĩa (nhiều True/False hơn)
- Intermediate (Trung bình): Hiểu và áp dụng (mix cả hai loại)  
- Advanced (Khó): Phân tích, tư duy phản biện (nhiều Multiple Choice hơn)

**Quy tắc định dạng:**
- Dùng **bold** để nhấn mạnh
- Dùng *italic* cho thuật ngữ
- Dùng ~~gạch ngang~~ cho ví dụ sai
- Dùng LaTeX cho công thức: $E = mc^2$ (inline) hoặc $$\\sum_{{i=1}}^n$$ (block)
- Phân số dùng $\\frac{{a}}{{b}}$ VÍ DỤ: $\\frac{{1}}{{2}}$, $\\frac{{3}}{{4}}$

Tạo {num_questions} câu hỏi. Trộn loại câu hỏi:
1. **Trắc nghiệm** (4 đáp án: A, B, C, D)
2. **Đúng/Sai** (2 đáp án: Đúng, Sai)

Trả về CHỈ JSON hợp lệ (không có markdown code blocks):
{{
    "title": "Tiêu đề quiz bằng tiếng Việt",
    "difficulty": "{difficulty}",
    "questions": [
        {{
            "type": "multiple_choice",
            "question": "Câu hỏi bằng tiếng Việt với **in đậm** hoặc $công thức$?",
            "options": ["A. Đáp án 1", "B. Đáp án 2", "C. Đáp án 3", "D. Đáp án 4"],
            "correct_answer": "A",
            "explanation": "Giải thích bằng tiếng Việt"
        }},
        {{
            "type": "true_false",
            "question": "Phát biểu cần đánh giá?",
            "options": ["Đúng", "Sai"],
            "correct_answer": "Đúng",
            "explanation": "Lý do đúng/sai"
        }}
    ]
}}
"""


def generate_quiz_from_image(
    pdf_path: str,
    page_number: int,
    difficulty: str = "Beginner",
    num_questions: int = 5
) -> Dict[str, Any]:
    """
    Generate quiz by sending PDF page as image to vision model.
    
    Args:
        pdf_path: Path to PDF file
        page_number: Page number to convert (1-indexed)
        difficulty: Beginner, Intermediate, or Advanced
        num_questions: Number of questions
        
    Returns:
        Quiz dict with mixed question types
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        raise ValueError("pdf2image not installed. Run: pip install pdf2image")
    
    # Validate difficulty
    if difficulty not in ["Beginner", "Intermediate", "Advanced"]:
        difficulty = "Beginner"
    
    # Convert PDF page to image
    try:
        images = convert_from_path(
            pdf_path, 
            first_page=page_number, 
            last_page=page_number,
            dpi=150  # Balance quality vs speed
        )
        if not images:
            raise ValueError(f"Could not convert page {page_number}")
        
        page_image = images[0]
    except Exception as e:
        raise ValueError(f"PDF conversion failed: {str(e)}")
    
    # Convert to base64
    buffered = BytesIO()
    page_image.save(buffered, format="PNG")
    image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    # Create vision model
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    
    llm = ChatGoogleGenerativeAI(
        model="gemma-3-27b-it",
        google_api_key=api_key,
        temperature=0.5
    )
    
    # Create message with image
    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": VISION_QUIZ_PROMPT.format(
                    difficulty=difficulty,
                    num_questions=num_questions
                )
            },
            {
                "type": "image_url",
                "image_url": f"data:image/png;base64,{image_base64}"
            }
        ]
    )
    
    # Generate
    response = llm.invoke([message])
    response_text = response.content
    
    # Clean up response
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]
    
    try:
        quiz_data = json.loads(response_text.strip())
    except json.JSONDecodeError as e:
        print(f"⚠️ Vision quiz JSON parse error: {e}")
        print(f"Response: {response_text[:500]}")
        quiz_data = {
            "title": "Quiz",
            "difficulty": difficulty,
            "questions": [],
            "error": "Failed to parse quiz response"
        }
    
    quiz_data["page_number"] = page_number
    quiz_data["source"] = "vision"
    
    return quiz_data
