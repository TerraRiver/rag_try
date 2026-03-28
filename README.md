# 领导人讲话 RAG 问答平台

基于 LangChain + ChromaDB + SiliconFlow（OpenAI 兼容 API）的本地知识库问答系统。
前端为 React + Vite，对话时支持“思考中”阶段反馈与计时；后端为 FastAPI。

## 技术栈

- 前端：React 18 + Vite + Tailwind CSS
- 后端：FastAPI + LangChain
- 向量库：ChromaDB（本地持久化）
- 检索：BM25 + 向量检索 + Reranker
- 模型服务：SiliconFlow OpenAI Compatible API
- 包管理：`uv`（后端）+ `npm`（前端）

## 项目结构

```text
rag_try/
├─ .env
├─ backend/
│  ├─ main.py
│  ├─ rag.py
│  ├─ ingest.py
│  ├─ pyproject.toml
│  └─ uv.lock
├─ frontend/
│  ├─ src/
│  ├─ package.json
│  └─ vite.config.js
└─ README.md
```

## 环境要求

- Python >= 3.10
- Node.js >= 18
- uv（https://docs.astral.sh/uv/）
- SiliconFlow API Key

## 环境变量

在项目根目录创建 `.env`：

```env
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxxxxxx
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1

LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
RERANKER_MODEL=Qwen/Qwen3-Reranker-8B
RERANKER_TOP_N=10

BACKEND_PORT=8000
CHROMA_DB_PATH=./chroma_db
DOCS_PATH=./docs
```

## 安装依赖

后端：

```bash
cd backend
uv sync
```

前端：

```bash
cd frontend
npm install
```

## 初始化知识库（首次执行）

当前 `ingest.py` 读取的是 `backend/docs/contentALL1-12298.csv` 这份讲话数据，
不是通用的 `.txt` / `.md` / `.pdf` 文档扫描模式。

```bash
cd backend
uv run python ingest.py
```

执行完成后会生成本地向量库目录（`backend/chroma_db`）。

## 启动方式

### 开发环境

后端：

```bash
cd backend
uv run python main.py
```

前端：

```bash
cd frontend
npm run dev
```

默认访问：

- 前端：http://localhost:5173
- 后端 API：http://localhost:8000
- Swagger：http://localhost:8000/docs

### 生产环境（推荐）

先构建前端：

```bash
cd frontend
npm run build
```

再启动后端（多 worker、关闭 reload）：

```bash
cd backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

> 上面这条命令就是生产环境推荐启动命令。

## API 说明

### `POST /api/chat`

普通问答接口，返回完整答案。

请求示例：

```json
{
  "query": "请总结某次讲话的核心观点",
  "history": [
    { "role": "user", "content": "上一轮问题" },
    { "role": "assistant", "content": "上一轮回答" }
  ]
}
```

### `POST /api/chat/stream`

流式阶段接口（NDJSON），用于前端实时显示：

- 已接收请求
- 理解问题
- 检索资料
- 生成答案
- 整理来源

最后会返回 `final` 事件（含 `answer` 和 `source_nodes`）。

## 常见问题

### 访问 `/` 返回 404

这是因为后端没有检测到 `frontend/dist`。请先执行：

```bash
cd frontend
npm run build
```

然后重启后端。

### 提示缺少 `rank_bm25`

执行：

```bash
cd backend
uv add rank-bm25
uv sync
```

## 维护命令

新增后端依赖：

```bash
cd backend
uv add <package-name>
```

重建向量库：

```bash
cd backend
# Windows PowerShell
Remove-Item -Recurse -Force .\chroma_db
uv run python ingest.py
```
