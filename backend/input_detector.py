import re
from urllib.parse import urlparse


def is_url(text: str) -> bool:
    """Detect whether the input string is a URL or plain text/topic."""
    text = text.strip()
    url_pattern = re.compile(
        r'^(https?://)'
        r'([a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,})'
        r'(:\d+)?'
        r'(/[^\s]*)?$'
    )
    if url_pattern.match(text):
        try:
            parsed = urlparse(text)
            return parsed.scheme in ('http', 'https') and bool(parsed.netloc)
        except Exception:
            return False
    return False
