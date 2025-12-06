"""
EMO2 - Interactive Quiz Generator
=================================
Generate and render interactive quizzes with auto-grading support.
"""

import json
import uuid
from datetime import datetime
from typing import Dict

import streamlit as st

from utils import process_latex_content


def generate_quiz(quiz_json: str) -> str:
    """
    Generate an interactive quiz from a JSON string.
    
    Args:
        quiz_json: JSON string with structure:
            {
                "title": "Quiz Title",
                "questions": [
                    {"id": 1, "type": "multiple_choice", "question": "...",
                     "options": [...], "correct": 0, "explanation": "..."}
                ]
            }
    
    Returns:
        Confirmation string with quiz ID.
    """
    try:
        quiz_data = json.loads(quiz_json)
        
        if 'questions' not in quiz_data:
            return "Error: Quiz must contain 'questions' array"
        
        if not quiz_data['questions']:
            return "Error: Quiz must have at least one question"
        
        if 'title' not in quiz_data:
            quiz_data['title'] = "Quiz"
        
        # Auto-detect question types
        for i, q in enumerate(quiz_data['questions']):
            if 'id' not in q:
                q['id'] = i + 1
            
            if 'type' not in q:
                if 'options' in q:
                    q['type'] = 'multiple_choice'
                elif isinstance(q.get('correct'), bool):
                    q['type'] = 'true_false'
                else:
                    q['type'] = 'short_answer'
        
        quiz_id = f"quiz_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        quiz_data['quiz_id'] = quiz_id
        quiz_data['created_at'] = datetime.now().isoformat()
        quiz_data['user_answers'] = {}
        quiz_data['submitted'] = False
        quiz_data['score'] = None
        
        if 'active_quizzes' not in st.session_state:
            st.session_state.active_quizzes = {}
        if 'quiz_data_store' not in st.session_state:
            st.session_state.quiz_data_store = {}
        
        st.session_state.active_quizzes[quiz_id] = quiz_data
        st.session_state.quiz_data_store[quiz_id] = quiz_data
        st.session_state.current_quiz_id = quiz_id
        
        num_questions = len(quiz_data['questions'])
        return f"QUIZ_CREATED:{quiz_id}|{quiz_data['title']}|{num_questions} questions"
        
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON format - {str(e)}"
    except Exception as e:
        return f"Error creating quiz: {str(e)}"


def check_answer(user_ans, correct_ans, q_type: str, question: dict) -> bool:
    """Check if user answer is correct."""
    if user_ans is None:
        return False
    if q_type in ('multiple_choice', 'true_false'):
        return user_ans == correct_ans
    return user_ans == correct_ans


def render_question_input(quiz: dict, question: dict, q_key: str, q_type: str):
    """Render the appropriate input widget for a question type."""
    q_id = str(question['id'])
    
    if q_type == 'multiple_choice':
        options = question.get('options', [])
        if not options:
            st.warning("No options provided")
            return
        
        current_val = quiz['user_answers'].get(q_id)
        has_latex = any('$' in str(opt) or '\\' in str(opt) for opt in options)
        
        if has_latex:
            for j, opt in enumerate(options):
                opt_text = process_latex_content(opt)
                is_selected = current_val == j
                cols = st.columns([0.08, 0.82, 0.1])
                with cols[0]:
                    st.markdown(f"**{chr(65+j)}.**" if not is_selected else "**✓**")
                with cols[1]:
                    st.markdown(opt_text)
                with cols[2]:
                    if st.button("Select" if not is_selected else "✓",
                               key=f"{q_key}_opt{j}",
                               type="primary" if is_selected else "secondary"):
                        quiz['user_answers'][q_id] = j
        else:
            option_labels = [f"{chr(65+j)}. {opt}" for j, opt in enumerate(options)]
            selected = st.radio(
                "Select answer:",
                options=range(len(options)),
                format_func=lambda x: option_labels[x],
                index=current_val,
                key=q_key,
                label_visibility="collapsed"
            )
            if selected is not None:
                quiz['user_answers'][q_id] = selected
    
    elif q_type == 'true_false':
        current_val = quiz['user_answers'].get(q_id)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("True", key=f"{q_key}_true",
                        type="primary" if current_val == True else "secondary",
                        use_container_width=True):
                quiz['user_answers'][q_id] = True
        with col2:
            if st.button("False", key=f"{q_key}_false",
                        type="primary" if current_val == False else "secondary",
                        use_container_width=True):
                quiz['user_answers'][q_id] = False
    
    else:
        options = question.get('options', [])
        if options:
            current_val = quiz['user_answers'].get(q_id)
            option_labels = [f"{chr(65+j)}. {opt}" for j, opt in enumerate(options)]
            selected = st.radio("Select:", options=range(len(options)),
                               format_func=lambda x: option_labels[x],
                               index=current_val, key=f"{q_key}_fallback",
                               label_visibility="collapsed")
            if selected is not None:
                quiz['user_answers'][q_id] = selected
        else:
            st.info("This question type is not supported for auto-grading")


@st.fragment
def render_quiz(quiz_id: str):
    """Render an interactive quiz in the Streamlit UI."""
    quiz = None
    
    if 'active_quizzes' in st.session_state:
        quiz = st.session_state.active_quizzes.get(quiz_id)
    
    if not quiz and 'quiz_data_store' in st.session_state:
        quiz = st.session_state.quiz_data_store.get(quiz_id)
        if quiz:
            if 'active_quizzes' not in st.session_state:
                st.session_state.active_quizzes = {}
            st.session_state.active_quizzes[quiz_id] = quiz
    
    if not quiz:
        st.info("📝 Quiz was generated but needs to be recreated.")
        return
    
    with st.container():
        st.markdown(f"### 📝 {quiz.get('title', 'Quiz')}")
        if quiz.get('description'):
            st.caption(quiz['description'])
        
        total_q = len(quiz['questions'])
        answered = len(quiz.get('user_answers', {}))
        st.progress(answered / total_q if total_q > 0 else 0,
                   text=f"Progress: {answered}/{total_q} answered")
        
        st.divider()
        
        type_icons = {"multiple_choice": "🔘", "true_false": "✓✗"}
        
        for i, question in enumerate(quiz['questions']):
            q_id = question['id']
            q_key = f"{quiz_id}_q{q_id}"
            q_type = question.get('type', 'multiple_choice')
            
            q_icon = type_icons.get(q_type, "🔘")
            q_text = process_latex_content(question['question'])
            st.markdown(f"**{i+1}. {q_text}** {q_icon}")
            
            if quiz.get('submitted'):
                user_ans = quiz['user_answers'].get(str(q_id))
                correct_ans = question.get('correct')
                is_correct = check_answer(user_ans, correct_ans, q_type, question)
                
                if q_type == 'multiple_choice':
                    options = question.get('options', [])
                    for j, opt in enumerate(options):
                        opt_text = process_latex_content(opt)
                        if j == correct_ans:
                            st.markdown(f"✅ **{opt_text}** ← Correct")
                        elif j == user_ans:
                            st.markdown(f"❌ ~~{opt_text}~~ ← Your answer")
                        else:
                            st.markdown(f"○ {opt_text}")
                elif q_type == 'true_false':
                    if is_correct:
                        st.success(f"✅ Your answer: {'True' if user_ans else 'False'} - Correct!")
                    else:
                        st.error(f"❌ Your answer: {'True' if user_ans else 'False'} - Expected: {'True' if correct_ans else 'False'}")
                else:
                    if is_correct:
                        st.success(f"✅ Your answer: {user_ans} - Correct!")
                    else:
                        st.error(f"❌ Your answer: {user_ans} - Expected: {correct_ans}")
                
                if question.get('explanation'):
                    exp_text = process_latex_content(question['explanation'])
                    st.info(f"💡 {exp_text}")
            else:
                render_question_input(quiz, question, q_key, q_type)
            
            st.markdown("---")
        
        if not quiz.get('submitted'):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("📊 Submit Quiz", key=f"{quiz_id}_submit", type="primary", use_container_width=True):
                    correct = sum(
                        1 for q in quiz['questions']
                        if check_answer(
                            quiz['user_answers'].get(str(q['id'])),
                            q.get('correct'),
                            q.get('type', 'multiple_choice'),
                            q
                        )
                    )
                    quiz['submitted'] = True
                    quiz['score'] = {'correct': correct, 'total': len(quiz['questions'])}
        else:
            score = quiz.get('score', {})
            correct = score.get('correct', 0)
            total = score.get('total', 0)
            percentage = (correct / total * 100) if total > 0 else 0
            
            if percentage >= 80:
                st.balloons()
                st.success(f"🎉 Excellent! Score: **{correct}/{total}** ({percentage:.0f}%)")
            elif percentage >= 60:
                st.success(f"👍 Good job! Score: **{correct}/{total}** ({percentage:.0f}%)")
            elif percentage >= 40:
                st.warning(f"📚 Keep practicing! Score: **{correct}/{total}** ({percentage:.0f}%)")
            else:
                st.error(f"💪 Don't give up! Score: **{correct}/{total}** ({percentage:.0f}%)")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🔄 Retry Quiz", key=f"{quiz_id}_retry", use_container_width=True):
                    quiz['submitted'] = False
                    quiz['user_answers'] = {}
                    quiz['score'] = None
