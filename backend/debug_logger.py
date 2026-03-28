import os
from datetime import datetime
from pathlib import Path

from env_loader import load_project_env

load_project_env()

DEBUG_RAG_LOGS = os.getenv("DEBUG_RAG_LOGS", "0") == "1"
DEBUG_RAG_LOG_PATH = Path(os.getenv("DEBUG_RAG_LOG_PATH", "./rag_debug.log"))


def debug_log(namespace: str, message: str) -> None:
    if not DEBUG_RAG_LOGS:
        return

    line = f"{datetime.now().isoformat(timespec='seconds')} [{namespace}] {message}\n"
    print(line.rstrip())

    try:
        DEBUG_RAG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with DEBUG_RAG_LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except Exception:
        pass
