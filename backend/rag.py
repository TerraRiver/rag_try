"""
rag.py — RAG 核心逻辑

- 初始化 LLM 和 Embedding（通过硅基流动 API）
- 加载本地 ChromaDB 向量库
- 提供 query_rag() 函数供 main.py 调用
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

load_dotenv()

# ──────────────────────────────────────────────
# 模型初始化
# ──────────────────────────────────────────────
_llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    base_url=os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
    temperature=0.7,
)

_embeddings = OpenAIEmbeddings(
    model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3"),
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    base_url=os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
)

# ──────────────────────────────────────────────
# 向量库（在 FastAPI 启动时加载）
# ──────────────────────────────────────────────
_vectorstore = None
_retriever = None


def load_vectorstore():
    """加载本地 ChromaDB，在 FastAPI lifespan 中调用。"""
    global _vectorstore, _retriever
    chroma_path = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    _vectorstore = Chroma(
        persist_directory=chroma_path,
        embedding_function=_embeddings,
    )
    _retriever = _vectorstore.as_retriever(search_kwargs={"k": 3})


# ──────────────────────────────────────────────
# Prompt 模板
# ──────────────────────────────────────────────
_PROMPT_TEMPLATE = """\
你是一个专业的领导人讲话研究助手。请根据「已知资料」回答用户的问题。
如果已知资料中没有相关内容，请如实说明，不要编造。

已知资料：
{context}
{history_text}
用户问题：{question}

请用中文详细回答："""

_prompt = ChatPromptTemplate.from_template(_PROMPT_TEMPLATE)


def _format_docs(docs) -> str:
    parts = []
    for i, doc in enumerate(docs, 1):
        meta = doc.metadata
        header = (
            f"[资料{i}] 《{meta.get('标题', '未知')}》"
            f"（{meta.get('来源', '')} · {meta.get('时间', '')}）"
        )
        # page_content 已含 header，直接截取正文部分（去掉注入的那段 header）
        content_lines = doc.page_content.split("\n\n", 1)
        body = content_lines[1] if len(content_lines) > 1 else doc.page_content
        parts.append(f"{header}\n{body}")
    return "\n\n".join(parts)


def _format_history(history: list) -> str:
    if not history:
        return ""
    lines = []
    for msg in history[-6:]:   # 最多保留最近 3 轮（6 条）
        role = "用户" if msg.get("role") == "user" else "助手"
        lines.append(f"{role}：{msg.get('content', '')}")
    return "\n对话历史：\n" + "\n".join(lines) + "\n"


def _format_source_node(doc) -> str:
    """将检索到的 Document 格式化为前端展示的来源摘要字符串。"""
    meta = doc.metadata
    title  = meta.get("标题", "未知")
    date   = meta.get("时间", "")
    source = meta.get("来源", "")
    link   = meta.get("链接", "")
    chunk_idx   = meta.get("chunk_index", 0)
    chunk_total = meta.get("chunk_total", 1)

    # 取正文摘要（去掉 header 行）
    content_parts = doc.page_content.split("\n\n", 1)
    body = content_parts[1] if len(content_parts) > 1 else doc.page_content
    snippet = body[:150] + "…" if len(body) > 150 else body

    chunk_info = f"（第 {chunk_idx+1}/{chunk_total} 段）" if chunk_total > 1 else ""
    source_line = f"📰 {source} · {date}" if source else date
    link_line   = f"\n🔗 {link}" if link else ""

    return f"《{title}》{chunk_info}\n{source_line}{link_line}\n{snippet}"


# ──────────────────────────────────────────────
# 对外接口
# ──────────────────────────────────────────────
def query_rag(question: str, history: list = None) -> dict:
    """
    执行 RAG 查询。
    返回 {"answer": str, "source_nodes": list[str]}
    """
    if _retriever is None:
        raise RuntimeError(
            "向量库未加载。请先运行 ingest.py 建立知识库，然后重启后端。"
        )

    # 检索相关 chunks
    docs = _retriever.invoke(question)

    # 构建生成链
    chain = (
        {
            "context":      lambda _: _format_docs(docs),
            "history_text": lambda _: _format_history(history or []),
            "question":     RunnablePassthrough(),
        }
        | _prompt
        | _llm
        | StrOutputParser()
    )

    answer = chain.invoke(question)

    # 格式化来源信息
    source_nodes = [_format_source_node(doc) for doc in docs]

    return {"answer": answer, "source_nodes": source_nodes}
