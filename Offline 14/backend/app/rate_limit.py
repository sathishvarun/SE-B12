"""Shared slowapi rate limiter. Routers use `@limiter.limit("5/minute")`."""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
