"""
ingest.py — 针对领导人讲话 CSV 的知识库初始化脚本

数据结构：原序号 | 标题 | 来源 | 时间 | 内容 | 原文刊登 | 链接 | 类型
编码：utf-8-sig（带 BOM 的 UTF-8）

使用方式：
    cd backend
    python ingest.py

策略：
  - 短讲话（内容 ≤ CHUNK_SIZE 字符）→ 整条作为一个 chunk
  - 长讲话 → 按中文自然句边界分块
  - page_content 只存纯正文，不含 header（避免相同 header 在向量空间中聚集干扰语义）
  - 元数据（标题/时间/来源/链接）随每个 chunk 存入 ChromaDB，检索时动态拼入 Prompt
  - 分批写入，避免内存/API 请求过大
"""

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

load_dotenv()

# ──────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────
DOCS_PATH     = os.getenv("DOCS_PATH", "./docs")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
CSV_FILENAME  = "contentALL1-12298.csv"

# 正文 chunk 大小（字符数，不含 header）
# 中文约 1 字 ≈ 1-2 token；600 字 ≈ 300-600 token，远低于 bge-m3 的 8192 上限
CHUNK_SIZE    = 600
CHUNK_OVERLAP = 80

# 分批写入 ChromaDB 的批次大小（根据 API 限速可调整）
BATCH_SIZE    = 1000


# ──────────────────────────────────────────────
# 1. 读取 CSV
# ──────────────────────────────────────────────
def load_csv(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, encoding="utf-8-sig", dtype=str)
    df.fillna("", inplace=True)
    print(f"  读取 {len(df)} 条记录，字段：{list(df.columns)}")
    return df


# ──────────────────────────────────────────────
# 2. 构建 Document 列表
# ──────────────────────────────────────────────
def build_documents(df: pd.DataFrame) -> list[Document]:
    """
    每行讲话 → 若干 LangChain Document。
    每个 Document 的 page_content = 纯正文（不含 header），
    metadata 保存结构化字段供检索结果展示及 Prompt 拼接。
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        # 优先在中文句子/段落边界切分
        separators=[
            "\n\n", "。\n", "！\n", "？\n", "；\n", "\n",
            "。", "！", "？", "；", "……", "，", " ", "",
        ],
        length_function=len,
    )

    documents: list[Document] = []
    skipped = 0

    for _, row in df.iterrows():
        content = row.get("内容", "").strip()
        title   = row.get("标题", "").strip()
        source  = row.get("来源", "").strip()
        date    = row.get("时间", "").strip()
        link    = row.get("链接", "").strip()
        seq_no  = row.get("原序号", "").strip()

        if not content or len(content) < 10:
            skipped += 1
            continue

        meta = {
            "原序号": seq_no,
            "标题":   title,
            "来源":   source,
            "时间":   date,
            "链接":   link,
        }

        if len(content) <= CHUNK_SIZE:
            # 短讲话：整条不拆，page_content 只存纯正文
            documents.append(Document(
                page_content=content,
                metadata={**meta, "chunk_index": 0, "chunk_total": 1},
            ))
        else:
            # 长讲话：按句子边界分块，page_content 只存纯正文
            chunks = splitter.split_text(content)
            for i, chunk in enumerate(chunks):
                documents.append(Document(
                    page_content=chunk,
                    metadata={**meta, "chunk_index": i, "chunk_total": len(chunks)},
                ))

    print(f"  跳过空/过短内容：{skipped} 条")
    return documents


# ──────────────────────────────────────────────
# 3. 分批写入 ChromaDB
# ──────────────────────────────────────────────
def write_to_chroma(documents: list[Document], embeddings: OpenAIEmbeddings):
    vectorstore = Chroma(
        persist_directory=CHROMA_DB_PATH,
        embedding_function=embeddings,
    )

    total = len(documents)
    for start in range(0, total, BATCH_SIZE):
        batch = documents[start : start + BATCH_SIZE]
        vectorstore.add_documents(batch)
        done = min(start + BATCH_SIZE, total)
        pct  = done / total * 100
        print(f"\r  进度：[{done}/{total}] {pct:.1f}%", end="", flush=True)

    # chromadb >= 0.4 后持久化自动完成，无需手动调用 persist()
    print()  # 换行
    return vectorstore


# ──────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────
def main():
    print("=" * 55)
    print("RAG 知识库初始化（领导人讲话 CSV 版）")
    print("=" * 55)

    csv_path = Path(DOCS_PATH) / CSV_FILENAME
    if not csv_path.exists():
        print(f"\n❌ 未找到文件：{csv_path}")
        return

    # Step 1: 读 CSV
    print(f"\n📂 读取 CSV：{csv_path}")
    df = load_csv(str(csv_path))

    # Step 2: 构建 documents
    print(f"\n✂️  构建 chunks（chunk_size={CHUNK_SIZE}，overlap={CHUNK_OVERLAP}）...")
    documents = build_documents(df)

    # 打印长度分布
    lengths = [len(d.page_content) for d in documents]
    print(f"  生成 chunk 数：{len(documents)}")
    print(f"  chunk 字符长度：min={min(lengths)}  max={max(lengths)}  "
          f"mean={int(sum(lengths)/len(lengths))}")

    # Step 3: 向量化 + 写入
    print(f"\n🔢 向量化写入 ChromaDB（{CHROMA_DB_PATH}）...")
    model_name = os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B")
    print(f"  Embedding 模型：{model_name}")
    print(f"  批次大小：{BATCH_SIZE}  （共 {-(-len(documents)//BATCH_SIZE)} 批）\n")

    embeddings = OpenAIEmbeddings(
        model=model_name,
        api_key=os.getenv("SILICONFLOW_API_KEY"),
        base_url=os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
    )

    write_to_chroma(documents, embeddings)

    print(f"\n🎉 完成！{len(documents)} 个 chunk 已写入 {CHROMA_DB_PATH}")
    print("   现在可以启动后端：python main.py\n")


if __name__ == "__main__":
    main()
