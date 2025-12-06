"""
EMO2 - Rendering and Streaming Utilities
=========================================
Common helper functions for text rendering, LaTeX processing, and streaming.
"""

import re
import time
import streamlit as st


def stream_data(text: str, delay: float = 0.02):
    """
    Generator function for simulated streaming (typing effect).
    
    Args:
        text: The full text to stream
        delay: Time delay between words (default 0.02s)
    
    Yields:
        Words one at a time with a space
    """
    if not isinstance(text, str):
        text = str(text)
    
    for word in text.split(" "):
        yield word + " "
        time.sleep(delay)


def render_message_with_latex(content: str):
    r"""
    Render a message with proper LaTeX support.
    Converts various LaTeX syntaxes to Streamlit-compatible format.
    Handles: \[...\], \(...\), $...$, $$...$$
    """
    if not content:
        return
    
    # Fix setext-style headers: text followed by line of === or ---
    content = re.sub(
        r'^([^\n#*`\-\>][^\n]*)\n(={3,}|-{3,})$',
        r'\1\n\n\2',
        content,
        flags=re.MULTILINE
    )
    
    # Convert \[...\] (display math) to $$ blocks
    content = re.sub(
        r'\\\[(.*?)\\\]',
        lambda m: f'\n\n$$\n{m.group(1).strip()}\n$$\n\n',
        content,
        flags=re.DOTALL
    )
    
    # Convert \(...\) (inline math) to $...$
    content = re.sub(
        r'\\\((.*?)\\\)',
        lambda m: f'${m.group(1).strip()}$',
        content,
        flags=re.DOTALL
    )
    
    # Fix standalone $$...$$ on single line - split them properly
    def fix_block_latex(match):
        latex = match.group(1).strip()
        return f'\n\n$$\n{latex}\n$$\n\n'
    
    content = re.sub(
        r'(?:^|\n)\s*\$\$([^$]+)\$\$\s*(?:\n|$)',
        fix_block_latex,
        content
    )
    
    # Clean up extra newlines
    content = re.sub(r'\n{4,}', '\n\n\n', content)
    
    # Render with markdown
    st.markdown(content, unsafe_allow_html=True)


def process_latex_content(text: str) -> str:
    """
    Process text to convert LaTeX syntax for display.
    Returns the processed string (doesn't render it).
    Handles: \\[...\\], \\(...\\), $...$, $$...$$
    """
    if not text:
        return text
    
    # Convert \[...\] (display math) to $$ blocks
    text = re.sub(
        r'\\\[(.+?)\\\]',
        lambda m: f'$${m.group(1).strip()}$$',
        text,
        flags=re.DOTALL
    )
    
    # Convert \(...\) (inline math) to $...$
    text = re.sub(
        r'\\\((.+?)\\\)',
        lambda m: f'${m.group(1).strip()}$',
        text,
        flags=re.DOTALL
    )
    
    return text
