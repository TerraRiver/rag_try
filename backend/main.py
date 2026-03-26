"""
main.py - FastAPI entrypoint

Run:
    cd backend
    uvicorn main:app --reload --port 8000
or:
    python main.py
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

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from rag import load_vectorstore

    try:
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
    query: str
    history: Optional[List[dict]] = []


class ChatResponse(BaseModel):
    answer: str
    source_nodes: List[str] = []


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    from rag import query_rag

    try:
        result = query_rag(request.query, request.history)
        return ChatResponse(**result)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"内部错误：{exc}")


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    from rag import query_rag

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

            def on_progress(stage: str, label: str) -> None:
                push_event({"type": "stage", "stage": stage, "label": label})

            result = query_rag(
                request.query,
                request.history,
                progress_callback=on_progress,
            )
            push_event(
                {
                    "type": "final",
                    "answer": result["answer"],
                    "source_nodes": result.get("source_nodes", []),
                }
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


DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"

if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        return FileResponse(DIST_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("BACKEND_PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
