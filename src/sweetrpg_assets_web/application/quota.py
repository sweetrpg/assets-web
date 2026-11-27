# -*- coding: utf-8 -*-
"""quota.py

Bounds the staged files one user can hold, by count and total bytes. The shared data volume is
the only record, so deletes and the reclaim job free room without any bookkeeping.
"""

__author__ = "Paul Schifferer <dm@sweetrpg.com>"


import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import redis
from flask import abort, current_app

from sweetrpg_assets_web.application.reclaim import STAGED_KINDS


LOCK_TIMEOUT_SECONDS = 60
LOCK_WAIT_SECONDS = 10


def _usage(base: Path, owner: str, replaced: Path) -> tuple[int, int]:
    """Counts the owner's staged assets and their bytes, leaving out the one being replaced.

    ponytail: lists every staged directory on each upload; index by owner if that gets slow.
    """
    owned = re.compile(rf"{re.escape(owner)}(-[0-9]+)?")
    count = size = 0
    for kind in STAGED_KINDS:
        try:
            entries = list(os.scandir(base / kind))
        except FileNotFoundError:
            continue
        for entry in entries:
            if not owned.fullmatch(entry.name) or Path(entry.path) == replaced:
                continue
            try:
                size += sum(file.stat().st_size for file in os.scandir(entry.path))
            except FileNotFoundError:
                continue  # deleted while we were counting
            count += 1
    return count, size


@contextmanager
def staged_upload_slot(owner: str, asset_dir: Path, size: int) -> Iterator[None]:
    """Holds the owner's lock while the caller writes `size` bytes to `asset_dir`. Aborts with
    409 if that would exceed a limit, and 503 if the limit can't be checked."""
    # Redis, because the lock has to hold across pods.
    lock = current_app.config["SESSION_REDIS"].lock(
        f"staged-upload-lock:{owner}", timeout=LOCK_TIMEOUT_SECONDS, blocking_timeout=LOCK_WAIT_SECONDS
    )
    try:
        acquired = lock.acquire()
    except redis.exceptions.RedisError:
        current_app.logger.exception("staged upload lock unavailable")
        acquired = False
    if not acquired:
        abort(503, description="Uploads are temporarily unavailable")

    try:
        base = Path(os.path.realpath(current_app.config["ASSET_DATA_PATH"]))
        try:
            count, used = _usage(base, owner, asset_dir)
        except OSError:
            current_app.logger.exception("staged usage unavailable")
            abort(503, description="Uploads are temporarily unavailable")

        if count + 1 > current_app.config["STAGED_MAX_FILES"] or used + size > current_app.config["STAGED_MAX_BYTES"]:
            current_app.logger.warning("staged upload limit reached", extra={"files": count, "bytes": used})
            abort(409, description="Pending upload limit reached")
        yield
    finally:
        try:
            lock.release()
        except redis.exceptions.RedisError:
            current_app.logger.warning("staged upload lock was not released; it expires on its own")
