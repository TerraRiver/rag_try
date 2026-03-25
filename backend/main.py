"""
main.py — FastAPI 入口

启动方式：
    cd backend
    uvicorn main:app --reload --port 8000
或：
    python main.py
"""

import os
from contextlib import asynccontextmanager
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()


# ──────────────────────────────────────────────
# Lifespan：启动时加载向量库
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    from rag import load_vectorstore
    try:
        load_vectorstore()
        print("✅ 向量库加载成功")
    except Exception as e:
        print(f"⚠️  向量库加载失败（可能尚未运行 ingest.py）：{e}")
    yield


app = FastAPI(title="RAG 知识库问答 API", lifespan=lifespan)

# ──────────────────────────────────────────────
# CORS（允许前端本地开发跨域访问）
# ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# 请求 / 响应模型
# ──────────────────────────────────────────────
class ChatRequest(BaseModel):
    query: str
    history: Optional[List[dict]] = []


class ChatResponse(BaseModel):
    answer: str
    source_nodes: List[str] = []


# ──────────────────────────────────────────────
# 路由
# ──────────────────────────────────────────────
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    from rag import query_rag
    try:
        result = query_rag(request.query, request.history)
        return ChatResponse(**result)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部错误：{e}")


@app.get("/health")
async def health():
    return {"status": "ok"}


# ──────────────────────────────────────────────
# 直接运行
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("BACKEND_PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
