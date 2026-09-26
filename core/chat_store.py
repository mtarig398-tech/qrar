"""Persists chat sessions as JSON files under the chats/ directory.

Writes are atomic (write to a temp file, then os.replace) so a crash or a
concurrent read never observes a half-written file, and reads tolerate a
corrupted or missing file by returning an empty session instead of raising.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

import config

_SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]+$")


def new_chat_id() -> str:
    return uuid.uuid4().hex


def _path_for(chat_id: str) -> Path:
    if not _SAFE_ID.match(chat_id):
        raise ValueError(f"Invalid chat id: {chat_id!r}")
    return config.CHATS_DIR / f"{chat_id}.json"


def list_chats() -> list[dict]:
    chats = []
    for file in sorted(config.CHATS_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        chats.append(
            {
                "id": file.stem,
                "title": data.get("title", "New chat"),
                "updated_at": data.get("updated_at", ""),
            }
        )
    return chats


def load_chat(chat_id: str) -> dict:
    path = _path_for(chat_id)
    if not path.exists():
        return {"id": chat_id, "title": "New chat", "messages": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"id": chat_id, "title": "New chat", "messages": []}


def save_chat(chat_id: str, title: str, messages: list[dict]) -> None:
    path = _path_for(chat_id)
    payload = {
        "id": chat_id,
        "title": title,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "messages": messages,
    }
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)  # atomic on both POSIX and Windows
