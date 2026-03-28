"""
rag.py — RAG 核心逻辑

- 初始化 LLM 和 Embedding（通过硅基流动 API）
- 加载本地 ChromaDB 向量库
- 提供 query_rag() 函数供 main.py 调用
"""

import os
from typing import Callable, Optional, Sequence

import httpx
import jieba
from debug_logger import debug_log
from env_loader import load_project_env
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_classic.retrievers import ContextualCompressionRetriever, EnsembleRetriever
from langchain_core.documents.compressor import BaseDocumentCompressor

load_project_env()


def _debug_log(message: str) -> None:
    debug_log("rag", message)

# ──────────────────────────────────────────────
# 模型初始化
# ──────────────────────────────────────────────
_llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    base_url=os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
    temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
)

_embeddings = OpenAIEmbeddings(
    model=os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B"),
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    base_url=os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
)

# ──────────────────────────────────────────────
# 向量库（在 FastAPI 启动时加载）
# ──────────────────────────────────────────────
_vectorstore = None
_candidate_retriever = None
_reranker = None
ProgressCallback = Optional[Callable[[str, str], None]]
TokenCallback = Optional[Callable[[str], None]]
MAX_HISTORY_MESSAGES = 4
MAX_HISTORY_CHARS_PER_MESSAGE = 400
MAX_SEARCH_QUERY_CHARS = 200
MAX_SESSION_SUMMARY_CHARS = 500


# ──────────────────────────────────────────────
# 中文分词（BM25 用）
# ──────────────────────────────────────────────
def _jieba_tokenize(text: str) -> list[str]:
    return list(jieba.cut_for_search(text))


# ──────────────────────────────────────────────
# SiliconFlow Reranker（调用远程 /rerank 接口）
# ──────────────────────────────────────────────
class SiliconFlowReranker(BaseDocumentCompressor):
    """用硅基流动的 rerank API 对候选文档重新排序。"""
    model: str
    api_key: str
    base_url: str
    top_n: int = 8

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks=None,
    ) -> Sequence[Document]:
        if not documents:
            return []
        url = self.base_url.rstrip("/") + "/rerank"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "query": query,
            "documents": [doc.page_content for doc in documents],
            "top_n": self.top_n,
        }
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            results = resp.json()["results"]
            return [documents[r["index"]] for r in results]
        except Exception as e:
            print(f"⚠️  Reranker 调用失败，降级为原顺序：{e}")
            return list(documents)[: self.top_n]


def load_vectorstore():
    """加载本地 ChromaDB，构建混合检索器（BM25 + 向量 + Reranker），在 FastAPI lifespan 中调用。"""
    global _vectorstore, _candidate_retriever, _reranker
    chroma_path = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    _vectorstore = Chroma(
        persist_directory=chroma_path,
        embedding_function=_embeddings,
    )

    # ── 1. 从 Chroma 分批取全量文档，构建 BM25 索引 ──────────────
    # SQLite 的 SQL 变量数有上限，需要分批 get() 避免 "too many SQL variables"
    FETCH_BATCH = 2000
    all_docs: list[Document] = []
    offset = 0
    while True:
        raw = _vectorstore.get(
            include=["documents", "metadatas"],
            limit=FETCH_BATCH,
            offset=offset,
        )
        batch_texts = raw.get("documents") or []
        batch_metas = raw.get("metadatas") or []
        if not batch_texts:
            break
        for text, meta in zip(batch_texts, batch_metas):
            if text:
                all_docs.append(Document(page_content=text, metadata=meta))
        offset += len(batch_texts)
        if len(batch_texts) < FETCH_BATCH:
            break
    print(f"  BM25 索引：共 {len(all_docs)} 个文档")

    bm25_retriever = BM25Retriever.from_documents(
        all_docs, preprocess_func=_jieba_tokenize, k=15
    )

    # ── 2. 向量检索器 ──────────────────────────────────────────────
    dense_retriever = _vectorstore.as_retriever(search_kwargs={"k": 15})

    # ── 3. 混合检索（RRF 融合） ────────────────────────────────────
    # weights: [BM25, dense]，偏向语义检索
    ensemble = EnsembleRetriever(
        retrievers=[bm25_retriever, dense_retriever],
        weights=[0.4, 0.6],
    )

    # ── 4. Reranker 精排 ───────────────────────────────────────────
    reranker = SiliconFlowReranker(
        model=os.getenv("RERANKER_MODEL", "Qwen/Qwen3-Reranker-8B"),
        api_key=os.getenv("SILICONFLOW_API_KEY", ""),
        base_url=os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
        top_n=int(os.getenv("RERANKER_TOP_N", "10")),
    )

    _candidate_retriever = ensemble
    _reranker = reranker

    # Warm up the retriever path once at startup so later requests don't do it lazily.
    ContextualCompressionRetriever(
        base_compressor=_reranker,
        base_retriever=ensemble,
    )


# ──────────────────────────────────────────────
# Prompt 模板
# ──────────────────────────────────────────────
_SYSTEM_PROMPT = """\
你是一个专业的领导人讲话研究助手。请依据「已知资料」回答用户问题。

回答规则（必须严格遵守）：
1. 事实依据只能来自已知资料，禁止使用外部常识或编造信息。
2. 会话摘要和最近几轮对话仅用于理解用户本轮提问中的代词和省略指代，不得作为事实证据。
3. 每一个自然段末尾都必须追加引用标注，格式为 [资料n]，可多个并列，如 [资料1][资料3]。
4. 引用编号 n 必须来自下方已知资料中的编号，且与该段内容对应。
5. 若资料不足以回答，直接回答“未在资料中找到明确依据。”并给出最相关的 [资料n]。
"""

_PROMPT_TEMPLATE = """\
会话摘要（仅用于理解延续话题）：
{session_summary}

最近几轮对话（仅用于理解指代）：
{recent_messages}

已知资料：
{context}

用户问题：{question}
"""

_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMPT),
        ("human", _PROMPT_TEMPLATE),
    ]
)


def _format_docs(docs) -> str:
    parts = []
    for i, doc in enumerate(docs, 1):
        meta = doc.metadata
        header = (
            f"[资料{i}] 《{meta.get('标题', '未知')}》"
            f"（{meta.get('来源', '')} · {meta.get('时间', '')}）"
        )
        parts.append(f"{header}\n{doc.page_content}")
    return "\n\n".join(parts)


def _format_recent_messages(messages: list) -> str:
    if not messages:
        return "（无）"
    lines = []
    for msg in messages[-MAX_HISTORY_MESSAGES:]:
        role = "用户" if msg.get("role") == "user" else "助手"
        content = " ".join(str(msg.get("content", "")).split())
        if len(content) > MAX_HISTORY_CHARS_PER_MESSAGE:
            content = content[:MAX_HISTORY_CHARS_PER_MESSAGE] + "…"
        lines.append(f"{role}：{content}")
    return "\n".join(lines) if lines else "（无）"


def _format_session_summary(summary: str) -> str:
    text = _normalize_session_summary(summary)
    return text if text else "（无）"


def _normalize_session_summary(summary: str) -> str:
    text = " ".join((summary or "").split())
    if len(text) > MAX_SESSION_SUMMARY_CHARS:
        text = text[:MAX_SESSION_SUMMARY_CHARS].rstrip() + "…"
    return text


def _normalize_search_query(text: str, fallback: str) -> str:
    query = " ".join((text or "").split())
    if not query:
        query = fallback.strip()
    if len(query) > MAX_SEARCH_QUERY_CHARS:
        query = query[:MAX_SEARCH_QUERY_CHARS].rstrip() + "…"
    return query or fallback.strip()


def _preview_text(text: str, limit: int = 160) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) > limit:
        return normalized[:limit].rstrip() + "…"
    return normalized


def _format_source_node(doc) -> str:
    """将检索到的 Document 格式化为前端展示的来源摘要字符串。"""
    meta = doc.metadata
    title  = meta.get("标题", "未知")
    date   = meta.get("时间", "")
    source = meta.get("来源", "")
    link   = meta.get("链接", "")
    chunk_idx   = meta.get("chunk_index", 0)
    chunk_total = meta.get("chunk_total", 1)

    snippet = doc.page_content[:150] + "…" if len(doc.page_content) > 150 else doc.page_content

    chunk_info = f"（第 {chunk_idx+1}/{chunk_total} 段）" if chunk_total > 1 else ""
    source_line = f"📰 {source} · {date}" if source else date
    link_line   = f"\n🔗 {link}" if link else ""

    return f"《{title}》{chunk_info}\n{source_line}{link_line}\n{snippet}"


# ──────────────────────────────────────────────
# 对外接口
# ──────────────────────────────────────────────
_REWRITE_TEMPLATE = """\
请根据以下对话历史，将用户的最新问题改写为一个完整、独立的搜索句子。
要求：不依赖任何代词或上下文指代，直接表达完整语义，不输出任何解释。

会话摘要：
{session_summary}

最近几轮对话：
{recent_messages}

最新问题：{question}

改写后的完整问题："""

_rewrite_prompt = ChatPromptTemplate.from_template(_REWRITE_TEMPLATE)


def _rewrite_query(question: str, session_summary: str, recent_messages: list) -> str:
    """多轮对话时，用 LLM 将含代词/指代的问题扩写为独立检索句。"""
    if not session_summary and not recent_messages:
        return _normalize_search_query(question, question)
    chain = _rewrite_prompt | _llm | StrOutputParser()
    try:
        rewritten = chain.invoke(
            {
                "session_summary": _format_session_summary(session_summary),
                "recent_messages": _format_recent_messages(recent_messages),
                "question": question,
            }
        ).strip()
        normalized = _normalize_search_query(rewritten, question)
        _debug_log(
            "rewrite "
            f"summary='{_preview_text(session_summary)}' "
            f"recent='{_preview_text(_format_recent_messages(recent_messages))}' "
            f"question='{_preview_text(question)}' "
            f"query='{_preview_text(normalized)}'"
        )
        return normalized
    except Exception:
        normalized = _normalize_search_query(question, question)
        _debug_log(
            f"rewrite fallback question='{_preview_text(question)}' query='{_preview_text(normalized)}'"
        )
        return normalized


def _retrieve_documents(
    search_query: str,
    report: Callable[[str, str], None],
) -> list[Document]:
    if _candidate_retriever is None or _reranker is None:
        raise RuntimeError(
            "向量库未加载。请先运行 ingest.py 建立知识库，然后重启后端。"
        )

    report("retrieve", "召回候选资料")
    candidates = _candidate_retriever.invoke(search_query)
    _debug_log(
        f"retrieve candidates={len(candidates)} query='{_preview_text(search_query)}'"
    )

    report("retrieve", "精排检索结果")
    reranked = _reranker.compress_documents(candidates, search_query)
    reranked_list = list(reranked)
    _debug_log(
        "rerank "
        f"results={len(reranked_list)} "
        f"top_titles={[doc.metadata.get('标题', '未知') for doc in reranked_list[:3]]}"
    )
    return reranked_list


def query_rag(
    question: str,
    session_summary: str = "",
    recent_messages: list | None = None,
    progress_callback: ProgressCallback = None,
) -> dict:
    """
    执行 RAG 查询。
    返回 {"answer": str, "source_nodes": list[str]}
    """
    if _candidate_retriever is None or _reranker is None:
        raise RuntimeError(
            "向量库未加载。请先运行 ingest.py 建立知识库，然后重启后端。"
        )

    def report(stage: str, label: str) -> None:
        if progress_callback:
            progress_callback(stage, label)

    report("rewrite", "理解问题")
    clean_question = question.strip()
    _debug_log(
        "query_rag "
        f"question='{_preview_text(clean_question)}' "
        f"summary='{_preview_text(session_summary)}' "
        f"recent_count={len(recent_messages or [])}"
    )
    search_query = _rewrite_query(clean_question, session_summary, recent_messages or [])

    docs = _retrieve_documents(search_query, report)

    report("generate", "生成答案")
    chain = (
        {
            "context":      lambda _: _format_docs(docs),
            "session_summary": lambda _: _format_session_summary(session_summary),
            "recent_messages": lambda _: _format_recent_messages(recent_messages or []),
            "question":     RunnablePassthrough(),
        }
        | _prompt
        | _llm
        | StrOutputParser()
    )

    answer = chain.invoke(clean_question)

    report("sources", "整理来源")
    source_nodes = [_format_source_node(doc) for doc in docs]

    return {"answer": answer, "source_nodes": source_nodes}


def _extract_chunk_text(chunk) -> str:
    """Normalize streamed model chunks into plain text."""
    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "".join(parts)
    return str(content) if content else ""


def query_rag_stream(
    question: str,
    session_summary: str = "",
    recent_messages: list | None = None,
    progress_callback: ProgressCallback = None,
    token_callback: TokenCallback = None,
) -> dict:
    """
    Execute a RAG query with token-level streaming callback.
    Returns {"answer": str, "source_nodes": list[str]} after streaming ends.
    """
    if _candidate_retriever is None or _reranker is None:
        raise RuntimeError(
            "向量库未加载。请先运行 ingest.py 建立知识库，然后重启后端。"
        )

    def report(stage: str, label: str) -> None:
        if progress_callback:
            progress_callback(stage, label)

    report("rewrite", "理解问题")
    clean_question = question.strip()
    _debug_log(
        "query_rag_stream "
        f"question='{_preview_text(clean_question)}' "
        f"summary='{_preview_text(session_summary)}' "
        f"recent_count={len(recent_messages or [])}"
    )
    search_query = _rewrite_query(clean_question, session_summary, recent_messages or [])

    docs = _retrieve_documents(search_query, report)

    prompt_value = _prompt.invoke(
        {
            "session_summary": _format_session_summary(session_summary),
            "recent_messages": _format_recent_messages(recent_messages or []),
            "context": _format_docs(docs),
            "question": clean_question,
        }
    )

    report("generate", "生成答案")
    answer_parts: list[str] = []
    for chunk in _llm.stream(prompt_value):
        token = _extract_chunk_text(chunk)
        if not token:
            continue
        answer_parts.append(token)
        if token_callback:
            token_callback(token)

    answer = "".join(answer_parts)

    report("sources", "整理来源")
    source_nodes = [_format_source_node(doc) for doc in docs]
    return {"answer": answer, "source_nodes": source_nodes}


_SUMMARY_TEMPLATE = """\
你在维护一个 RAG 会话摘要。请基于已有摘要和最新对话，输出新的会话摘要。

要求：
1. 只保留后续检索和回答真正需要的上下文。
2. 重点记录持续讨论的主题、明确限定条件、已确认的结论、仍未解决的问题。
3. 不要逐轮复述，不要编造，不要使用项目符号。
4. 输出控制在 200 字以内，只输出摘要正文。

已有摘要：
{previous_summary}

最新对话：
{recent_messages}

新的会话摘要："""

_summary_prompt = ChatPromptTemplate.from_template(_SUMMARY_TEMPLATE)


def refresh_session_summary(previous_summary: str, recent_messages: list | None) -> str:
    chain = _summary_prompt | _llm | StrOutputParser()
    try:
        summary = chain.invoke(
            {
                "previous_summary": _format_session_summary(previous_summary),
                "recent_messages": _format_recent_messages(recent_messages or []),
            }
        ).strip()
        normalized = _normalize_session_summary(summary)
        _debug_log(
            "summary refresh "
            f"previous='{_preview_text(previous_summary)}' "
            f"recent='{_preview_text(_format_recent_messages(recent_messages or []))}' "
            f"next='{_preview_text(normalized)}'"
        )
        return normalized
    except Exception:
        normalized = _normalize_session_summary(previous_summary)
        _debug_log(
            f"summary refresh fallback previous='{_preview_text(normalized)}'"
        )
        return normalized
