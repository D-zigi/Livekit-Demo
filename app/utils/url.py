"""
URL Utilities
"""
from typing import Optional
from urllib.parse import urlencode, urlunparse, urlparse

def build_url(
    base_url: str,
    path: str = '/',
    params: Optional[dict] = None
) -> str:
    """
    Build a URL from the base URL, path, and query parameters.
    """
    # Parse the base URL to extract the scheme and netloc
    parsed_base = urlparse(base_url)
    scheme = parsed_base.scheme
    netloc = parsed_base.netloc

    # If base_url doesn't have a scheme, assume it's the netloc
    if not scheme and not netloc:
        netloc = base_url
        scheme = "https"  # Default to https if no scheme provided

    # Create query string from params
    query = urlencode(params) if params else ''

    # Use urlunparse with all 6 required components
    url = urlunparse((scheme, netloc, path, '', query, ''))
    return url
