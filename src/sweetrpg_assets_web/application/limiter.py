# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""limiter.py
Process-wide rate limit: one shared bucket across every route and every client, not per-client
throttling - matches the Go services' `golang.org/x/time/rate` middleware convention (a blunt
backstop, not real per-client rate limiting). The key function returns a constant so every
request shares the same bucket regardless of caller; the limit string comes from `RATE_LIMIT`
via `BaseConfig`, applied globally in `create_app`.
"""

from flask_limiter import Limiter


limiter = Limiter(key_func=lambda: "global")
