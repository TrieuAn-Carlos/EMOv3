"""
EMO Backend - Web Integrations
==============================
Web page reading, YouTube transcripts, news headlines.
Migrated from web_tools.py
"""

import re
import requests
from typing import Optional
from urllib.parse import urljoin

from youtube_transcript_api import YouTubeTranscriptApi


def read_web_page(url: str, extract_type: str = "content") -> str:
    """Fetch and return content from a web page."""
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        if extract_type in ["news", "links"]:
            return _extract_structured_content(url, extract_type)
        
        # Method 1: Jina Reader API
        try:
            jina_url = f"https://r.jina.ai/{url}"
            response = requests.get(jina_url, timeout=10, headers={
                "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1)"
            })
            
            if response.status_code == 200:
                content = response.text.strip()
                if content and len(content) > 100 and not content.startswith("Error"):
                    if len(content) > 20000:
                        content = content[:20000] + "\n\n[...Truncated...]"
                    return f"=== WEB CONTENT ===\nSource: {url}\n---\n{content}\n=== END ==="
        except:
            pass
        
        # Method 2: BeautifulSoup fallback
        try:
            from bs4 import BeautifulSoup
            
            response = requests.get(url, timeout=10, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            for script in soup(["script", "style", "meta", "link"]):
                script.decompose()
            
            main = soup.find("main") or soup.find("article") or soup.find("body") or soup
            
            parts = []
            title = soup.find("h1")
            if title:
                parts.append(f"# {title.get_text(strip=True)}\n")
            
            for elem in main.find_all(["h2", "h3", "h4", "p", "li"]):
                text = elem.get_text(strip=True)
                if text and len(text) > 10:
                    if elem.name.startswith("h"):
                        parts.append(f"{'#' * (int(elem.name[1]) + 1)} {text}")
                    else:
                        parts.append(text)
            
            content = "\n\n".join(parts)
            if content and len(content) > 100:
                if len(content) > 20000:
                    content = content[:20000] + "\n\n[...Truncated...]"
                return f"=== WEB CONTENT ===\nSource: {url}\n---\n{content}\n=== END ==="
        except:
            pass
        
        return f"Error: Could not retrieve content from {url}"
    except Exception as e:
        return f"Error: {str(e)[:80]}"


def _extract_structured_content(url: str, extract_type: str) -> str:
    """Extract news headlines or links."""
    try:
        from bs4 import BeautifulSoup
        
        response = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.5,vi;q=0.3",
        })
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        for elem in soup(["script", "style", "nav", "footer", "header", "aside"]):
            elem.decompose()
        
        items = []
        seen = set()
        
        if extract_type == "news":
            for a in soup.find_all("a", href=True):
                try:
                    title = a.get_text(strip=True)
                    href = str(a.get("href", ""))
                    
                    if not title or not href:
                        continue
                    
                    if (15 < len(title) < 300
                        and title.lower() not in seen
                        and not href.startswith(("#", "javascript:", "mailto:"))):
                        seen.add(title.lower())
                        items.append({"title": title, "url": urljoin(url, href)})
                except:
                    continue
            
            items.sort(key=lambda x: len(x["title"]), reverse=True)
            items = items[:15]
            
            if items:
                result = f"=== NEWS from {url} ===\n\n"
                for i, item in enumerate(items, 1):
                    result += f"{i}. **{item['title']}**\n   {item['url']}\n\n"
                return result
        
        return f"No content found at {url}"
    except Exception as e:
        return f"Error: {str(e)[:80]}"


def get_news_headlines(url: str, count: int = 10) -> str:
    """Extract news headlines from a news website."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return _extract_structured_content(url, "news")


def watch_youtube(video_url: str) -> str:
    """Fetch YouTube video transcript."""
    try:
        # Extract video ID
        video_id = None
        match = re.search(r"[?&]v=([a-zA-Z0-9_-]{11})", video_url)
        if match:
            video_id = match.group(1)
        
        if not video_id:
            match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", video_url)
            if match:
                video_id = match.group(1)
        
        if not video_id:
            return "Error: Could not extract video ID"
        
        ytt = YouTubeTranscriptApi()
        transcript = None
        language = None
        
        # Try English, Vietnamese
        for lang_code, lang_name in [("en", "English"), ("vi", "Vietnamese")]:
            try:
                transcript = ytt.fetch(video_id, languages=[lang_code])
                language = lang_name
                break
            except:
                continue
        
        if not transcript:
            try:
                available = ytt.list(video_id)
                for t in available:
                    try:
                        transcript = t.fetch()
                        language = t.language
                        break
                    except:
                        continue
            except:
                return "Error: No transcript available"
        
        if not transcript:
            return "Error: Transcript empty"
        
        # Format with timestamps
        parts = []
        current_min = 0
        current_texts = []
        
        for entry in transcript:
            text = entry.text if hasattr(entry, "text") else entry.get("text", "")
            start = entry.start if hasattr(entry, "start") else entry.get("start", 0)
            
            if not text:
                continue
            
            entry_min = int(start // 60)
            
            if entry_min > current_min:
                if current_texts:
                    parts.append(f"[{current_min:02d}:00] {' '.join(current_texts)}")
                current_min = entry_min
                current_texts = [text]
            else:
                current_texts.append(text)
        
        if current_texts:
            parts.append(f"[{current_min:02d}:00] {' '.join(current_texts)}")
        
        return f"""=== YOUTUBE TRANSCRIPT ===
Video: {video_id}
Language: {language or 'Unknown'}
---
{chr(10).join(parts)}
=== END ==="""
    
    except Exception as e:
        return f"Error: {str(e)[:100]}"
