"""
EMO2 - Web Tools
================
Web page reading, YouTube transcripts, and news headline extraction.
"""

import re
import requests
from typing import Optional
from urllib.parse import urljoin

from youtube_transcript_api import YouTubeTranscriptApi


def read_web_page(url: str, extract_type: str = "content") -> str:
    """
    Fetch and return content from a web page.
    
    Args:
        url: The URL of the web page to read.
        extract_type: "content" for general, "news" for headlines, "links" for all links.
    
    Returns:
        Extracted content based on extract_type.
    """
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        if extract_type in ["news", "links"]:
            return _extract_structured_content(url, extract_type)
        
        # Method 1: Jina Reader API
        try:
            jina_url = f"https://r.jina.ai/{url}"
            response = requests.get(jina_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
            })
            
            if response.status_code == 200:
                content = response.text.strip()
                if content and len(content) > 100 and not content.startswith('Error'):
                    if len(content) > 20000:
                        content = content[:20000] + "\n\n[...Content Truncated...]"
                    return f"=== WEB CONTENT ===\nSource: {url}\n---\n{content}\n=== END CONTENT ==="
        except Exception:
            pass
        
        # Method 2: BeautifulSoup fallback
        try:
            from bs4 import BeautifulSoup
            
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            for script in soup(["script", "style", "meta", "link"]):
                script.decompose()
            
            main_content = soup.find('main') or soup.find('article') or soup.find('body') or soup
            
            text_parts = []
            title = soup.find('h1')
            if title:
                text_parts.append(f"# {title.get_text(strip=True)}\n")
            
            for elem in main_content.find_all(['h2', 'h3', 'h4', 'p', 'li']):
                text = elem.get_text(strip=True)
                if text and len(text) > 10:
                    if elem.name.startswith('h'):
                        text_parts.append(f"{'#' * (int(elem.name[1]) + 1)} {text}")
                    else:
                        text_parts.append(text)
            
            content = "\n\n".join(text_parts)
            
            if content and len(content) > 100:
                if len(content) > 20000:
                    content = content[:20000] + "\n\n[...Truncated...]"
                return f"=== WEB CONTENT ===\nSource: {url}\n---\n{content}\n=== END CONTENT ==="
        except ImportError:
            return "Error: beautifulsoup4 not installed"
        except Exception:
            pass
        
        return f"Error: Could not retrieve content from {url}"
    except Exception as e:
        return f"Error: Failed to read web page. {str(e)[:80]}"


def _extract_structured_content(url: str, extract_type: str) -> str:
    """Extract news headlines or links from a webpage."""
    try:
        from bs4 import BeautifulSoup
        
        response = requests.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.5,vi;q=0.3',
        })
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        for elem in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form']):
            elem.decompose()
        
        items = []
        seen_titles = set()
        
        if extract_type == "news":
            for a_tag in soup.find_all('a', href=True):
                try:
                    title = a_tag.get_text(strip=True)
                    href = str(a_tag.get('href', ''))
                    
                    if not title or not href:
                        continue
                    
                    title_len = len(title)
                    if (15 < title_len < 300
                        and title.lower() not in seen_titles
                        and not href.startswith(('#', 'javascript:', 'mailto:'))
                        and not any(s in href.lower() for s in ['/tag/', '/category/', '/login'])):
                        
                        seen_titles.add(title.lower())
                        items.append({'title': title, 'url': urljoin(url, href)})
                except Exception:
                    continue
            
            items.sort(key=lambda x: len(x['title']), reverse=True)
            items = items[:15]
            
            if items:
                result = f"=== NEWS HEADLINES from {url} ===\n\n"
                for i, item in enumerate(items, 1):
                    result += f"{i}. **{item['title']}**\n   🔗 {item['url']}\n\n"
                return result
            return f"Could not extract headlines from {url}"
        
        elif extract_type == "links":
            for a_tag in soup.find_all('a', href=True):
                try:
                    title = a_tag.get_text(strip=True)
                    href = str(a_tag.get('href', ''))
                    
                    if title and len(title) > 5 and href and not href.startswith('#'):
                        if title.lower() not in seen_titles:
                            seen_titles.add(title.lower())
                            items.append({'title': title, 'url': urljoin(url, href)})
                except Exception:
                    continue
            
            items = items[:30]
            if items:
                result = f"=== LINKS from {url} ===\n\n"
                for i, item in enumerate(items, 1):
                    result += f"{i}. {item['title']}: {item['url']}\n"
                return result
        
        return f"No structured content found at {url}"
    except ImportError:
        return "Error: beautifulsoup4 not installed"
    except Exception as e:
        return f"Error extracting from {url}: {str(e)[:80]}"


def get_news_headlines(url: str, count: int = 10) -> str:
    """Extract news headlines from a news website."""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    count = min(max(count, 1), 20)
    result = _extract_structured_content(url, "news")
    
    if "===" in result and "Could not" not in result:
        lines = result.split('\n')
        header = lines[:2]
        items = []
        current_item = []
        
        for line in lines[2:]:
            if line.strip() and line.strip()[0].isdigit() and '.' in line[:4]:
                if current_item:
                    items.append('\n'.join(current_item))
                current_item = [line]
            elif current_item:
                current_item.append(line)
        
        if current_item:
            items.append('\n'.join(current_item))
        
        items = items[:count]
        return '\n'.join(header) + '\n' + '\n'.join(items)
    
    return result


def watch_youtube(video_url: str) -> str:
    """
    Fetch YouTube video transcript with 60-second time blocks.
    
    Args:
        video_url: YouTube URL (supports youtube.com/watch?v= and youtu.be/ formats)
    
    Returns:
        Formatted transcript with timestamps.
    """
    try:
        # Extract video ID
        video_id = None
        match = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', video_url)
        if match:
            video_id = match.group(1)
        
        if not video_id:
            match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', video_url)
            if match:
                video_id = match.group(1)
        
        if not video_id:
            return "Error: Could not extract video ID from URL"
        
        ytt = YouTubeTranscriptApi()
        transcript = None
        language_used = None
        
        # Try English, Vietnamese, then any available
        for lang_code, lang_name in [('en', 'English'), ('vi', 'Vietnamese')]:
            try:
                transcript = ytt.fetch(video_id, languages=[lang_code])
                language_used = lang_name
                break
            except Exception:
                continue
        
        if not transcript:
            try:
                available = ytt.list(video_id)
                for t in available:
                    try:
                        transcript = t.fetch()
                        language_used = t.language
                        break
                    except Exception:
                        continue
            except Exception as e:
                return f"Error: Could not retrieve transcript. {str(e)[:50]}"
        
        if not transcript:
            return "Error: Transcript was empty"
        
        # Group into 60-second chunks
        formatted_parts = []
        current_minute = 0
        current_texts = []
        
        for entry in transcript:
            text = entry.text if hasattr(entry, 'text') else entry.get('text', '')
            start = entry.start if hasattr(entry, 'start') else entry.get('start', 0)
            
            if not text:
                continue
            
            entry_minute = int(start // 60)
            
            if entry_minute > current_minute:
                if current_texts:
                    formatted_parts.append(f"[{current_minute:02d}:00] {' '.join(current_texts)}")
                current_minute = entry_minute
                current_texts = [text]
            else:
                current_texts.append(text)
        
        if current_texts:
            formatted_parts.append(f"[{current_minute:02d}:00] {' '.join(current_texts)}")
        
        if not formatted_parts:
            return "Error: Transcript was empty"
        
        return f"""=== YOUTUBE TRANSCRIPT ===
Video ID: {video_id}
Language: {language_used or 'Unknown'}
---
{chr(10).join(formatted_parts)}
=== END TRANSCRIPT ==="""
    
    except ImportError:
        return "Error: youtube-transcript-api not installed"
    except Exception as e:
        return f"Error: Could not retrieve transcript. {str(e)[:100]}"
