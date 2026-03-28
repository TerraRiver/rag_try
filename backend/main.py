"""
main.py - FastAPI entrypoint

Development:
    cd backend
    uv run python main.py

Production:
    uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
"""

import asyncio
import json
import os
import queue
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from debug_logger import debug_log
from env_loader import load_project_env
from rag import query_rag, query_rag_stream, refresh_session_summary
from session_store import (
    DEFAULT_HISTORY_MESSAGE_LIMIT,
    append_messages,
    get_session_messages,
    get_session_context,
    init_session_db,
    update_session_summary,
)

load_project_env()


def _debug_log(message: str) -> None:
    debug_log("api", message)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from rag import load_vectorstore

    try:
        init_session_db()
        load_vectorstore()
        print("向量库加载成功")
    except Exception as exc:
        print(f"向量库加载失败（可能尚未运行 ingest.py）：{exc}")
    yield


app = FastAPI(title="RAG 知识库问答 API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    query: str


class ChatResponse(BaseModel):
    answer: str
    source_nodes: List[str] = Field(default_factory=list)


class SessionMessage(BaseModel):
    id: str
    role: str
    content: str
    source_nodes: List[str] = Field(default_factory=list)


class SessionDetailResponse(BaseModel):
    session_id: str
    summary: str = ""
    messages: List[SessionMessage] = Field(default_factory=list)


def _persist_turn_and_refresh_summary(
    session_id: str,
    user_query: str,
    answer: str,
    previous_summary: str,
    source_nodes: Optional[List[str]] = None,
) -> None:
    _debug_log(
        f"persist turn session_id={session_id} query_len={len(user_query)} answer_len={len(answer)}"
    )
    append_messages(
        session_id,
        [
            {"role": "user", "content": user_query},
            {
                "role": "assistant",
                "content": answer,
                "source_nodes": source_nodes or [],
            },
        ],
    )

    def summary_worker() -> None:
        try:
            _, recent_messages = get_session_context(session_id)
            next_summary = refresh_session_summary(previous_summary, recent_messages)
            if next_summary:
                update_session_summary(session_id, next_summary)
        except Exception as exc:
            print(f"会话摘要更新失败：{exc}")

    threading.Thread(target=summary_worker, daemon=True).start()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        _debug_log(f"chat request session_id={request.session_id} query='{request.query[:120]}'")
        session_summary, recent_messages = await run_in_threadpool(
            get_session_context,
            request.session_id,
        )
        result = await run_in_threadpool(
            query_rag,
            request.query,
            session_summary=session_summary,
            recent_messages=recent_messages,
        )
        await run_in_threadpool(
            _persist_turn_and_refresh_summary,
            request.session_id,
            request.query,
            result["answer"],
            session_summary,
            result.get("source_nodes", []),
        )
        return ChatResponse(**result)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"内部错误：{exc}")


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    started_at = time.monotonic()
    event_queue: "queue.Queue[dict | None]" = queue.Queue()

    def elapsed_ms() -> int:
        return int((time.monotonic() - started_at) * 1000)

    def push_event(event: dict) -> None:
        event.setdefault("elapsed_ms", elapsed_ms())
        event_queue.put(event)

    def worker() -> None:
        try:
            push_event({"type": "stage", "stage": "queued", "label": "请求已接收"})
            _debug_log(
                f"chat_stream request session_id={request.session_id} query='{request.query[:120]}'"
            )
            session_summary, recent_messages = get_session_context(request.session_id)

            def on_progress(stage: str, label: str) -> None:
                push_event({"type": "stage", "stage": stage, "label": label})

            def on_token(token: str) -> None:
                push_event({"type": "delta", "delta": token})

            result = query_rag_stream(
                request.query,
                session_summary=session_summary,
                recent_messages=recent_messages,
                progress_callback=on_progress,
                token_callback=on_token,
            )
            push_event(
                {
                    "type": "final",
                    "answer": result["answer"],
                    "source_nodes": result.get("source_nodes", []),
                }
            )
            _persist_turn_and_refresh_summary(
                request.session_id,
                request.query,
                result["answer"],
                session_summary,
                result.get("source_nodes", []),
            )
        except RuntimeError as exc:
            push_event(
                {
                    "type": "error",
                    "code": "service_unavailable",
                    "error": str(exc),
                }
            )
        except Exception as exc:
            push_event(
                {
                    "type": "error",
                    "code": "internal_error",
                    "error": f"内部错误：{exc}",
                }
            )
        finally:
            event_queue.put(None)

    threading.Thread(target=worker, daemon=True).start()

    async def event_stream():
        while True:
            event = await asyncio.to_thread(event_queue.get)
            if event is None:
                break
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson; charset=utf-8",
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    limit: int = Query(default=DEFAULT_HISTORY_MESSAGE_LIMIT, ge=1, le=500),
):
    session_summary, _ = await run_in_threadpool(get_session_context, session_id)
    messages = await run_in_threadpool(get_session_messages, session_id, limit)
    return SessionDetailResponse(
        session_id=session_id,
        summary=session_summary,
        messages=[SessionMessage(**message) for message in messages],
    )


DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/")
    async def serve_frontend_root():
        return FileResponse(DIST_DIR / "index.html")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        return FileResponse(DIST_DIR / "index.html")
else:
    print(f"frontend dist not found: {DIST_DIR}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("BACKEND_PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
