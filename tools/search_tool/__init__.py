"""
Search Tool Package

This package provides search functionality using SearXNG.
"""

from .searxng_search import (
    search_web,
    SafeSearchLevel,
    SearchResult,
    function_schema,
)

__all__ = ["search_web", "SafeSearchLevel", "SearchResult", "function_schema"]
