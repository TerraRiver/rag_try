# 领导人讲话 RAG 问答平台

基于 `LangChain + ChromaDB + SiliconFlow(OpenAI 兼容 API)` 的本地知识库问答系统。  
前端使用 `React + Vite`，后端使用 `FastAPI`，支持：

- 混合检索：BM25 + 向量检索 + Reranker
- 流式回答：前端实时显示阶段进度和增量输出
- 多轮对话：后端维护会话摘要和最近消息
- 来源回溯：回答附带来源片段
- 会话恢复：刷新页面后可恢复最近一段历史消息

## 技术栈

- 前端：React 18 + Vite + Tailwind CSS
- 后端：FastAPI + LangChain
- 向量库：ChromaDB
- 模型服务：SiliconFlow OpenAI Compatible API
- 包管理：`uv`（后端）+ `npm`（前端）

## 项目结构

```text
rag_try/
├─ .env
├─ .env.example
├─ .env.local                # 本机私密配置，不入库
├─ backend/
│  ├─ main.py
│  ├─ rag.py
│  ├─ ingest.py
│  ├─ session_store.py
│  ├─ env_loader.py
│  ├─ pyproject.toml
│  ├─ uv.lock
│  ├─ chroma_db/             # ingest 后生成
│  └─ docs/
│     ├─ README.md
│     └─ contentALL1-12298.csv
├─ frontend/
│  ├─ src/
│  ├─ package.json
│  └─ vite.config.js
└─ README.md
```

## 环境要求

- Python >= 3.10
- Node.js >= 18
- `uv`
- SiliconFlow API Key

## 环境变量

项目按两层配置读取：

- `.env` / `.env.example`：可公开的默认配置
- `.env.local`：本机私密配置，优先级更高，适合放真实 API Key

后端会先加载 `.env`，再用 `.env.local` 覆盖；前端开发代理也会读取项目根目录下的这些变量。

推荐做法：

1. 保留一个不含密钥的 `.env`
2. 把真实密钥写到 `.env.local`

示例：

```env
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxxxxxx
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1

LLM_MODEL=deepseek-ai/DeepSeek-V3.2
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
RERANKER_MODEL=Qwen/Qwen3-Reranker-8B
RERANKER_TOP_N=10

BACKEND_PORT=8000
FRONTEND_PORT=5173

CHROMA_DB_PATH=./chroma_db
DOCS_PATH=./docs

SESSION_DB_PATH=./session_state.db
SESSION_RECENT_MESSAGE_LIMIT=4
SESSION_HISTORY_MESSAGE_LIMIT=40
SESSION_MAX_STORED_MESSAGES=120

DEBUG_RAG_LOGS=0
DEBUG_RAG_LOG_PATH=./rag_debug.log
```

### 会话相关变量说明

- `SESSION_RECENT_MESSAGE_LIMIT`：问答时参与上下文拼接的最近消息数
- `SESSION_HISTORY_MESSAGE_LIMIT`：恢复历史接口默认返回的消息数
- `SESSION_MAX_STORED_MESSAGES`：单个会话最多保留多少条消息，超出后自动裁剪旧消息

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

## 初始化知识库

当前项目的 `ingest.py` 是针对 `backend/docs/contentALL1-12298.csv` 这份讲话数据写的，  
不是通用的 `.txt` / `.md` / `.pdf` 文档扫描模式。

执行方式：

```bash
cd backend
uv run python ingest.py
```

执行完成后会在 `backend/chroma_db/` 下生成本地向量库。

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

默认访问地址：

- 前端：http://localhost:5173
- 后端 API：http://localhost:8000
- Swagger：http://localhost:8000/docs

### 生产环境

先构建前端：

```bash
cd frontend
npm run build
```

再启动后端：

```bash
cd backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

说明：

- `frontend/dist` 存在时，后端会直接托管前端静态资源
- 生产环境建议关闭 `reload`
- 当前后端会话状态保存在本地 SQLite 文件中

## API 说明

### `POST /api/chat`

普通问答接口，返回完整答案。

请求示例：

```json
{
  "session_id": "9b6df7f5-7d97-4cd2-9149-df37a1fbad76",
  "query": "请总结某次讲话的核心观点"
}
```

响应示例：

```json
{
  "answer": "……",
  "source_nodes": [
    "《标题》\n📰 来源 · 时间\n片段摘要"
  ]
}
```

### `POST /api/chat/stream`

流式接口，返回 `NDJSON`，用于前端实时显示阶段推进和增量 token。

阶段包括：

- `queued`
- `rewrite`
- `retrieve`
- `generate`
- `sources`

最后会返回 `final` 事件，包含：

- `answer`
- `source_nodes`

### `GET /api/sessions/{session_id}`

读取指定会话的摘要和最近一段历史消息，用于前端刷新后恢复会话。

查询参数：

- `limit`：返回的消息条数，默认取 `SESSION_HISTORY_MESSAGE_LIMIT`

说明：

- 后端不会无限保存会话消息
- 超过 `SESSION_MAX_STORED_MESSAGES` 后会自动裁剪旧消息

## 当前实现特点

### 检索链路

后端当前采用以下顺序：

1. 使用会话摘要和最近消息改写检索问题
2. 用 BM25 + 向量检索召回候选文档
3. 调用 SiliconFlow rerank 接口做精排
4. 基于精排结果生成回答

### 会话恢复

- 前端在本地保存 `session_id`
- 刷新页面后，会调用 `GET /api/sessions/{session_id}` 恢复最近一段消息
- 会恢复助手消息对应的来源信息

### 历史裁剪

- 问答上下文只读取最近几条消息，不会无限拼接
- SQLite 中每个会话的消息量有上限
- 前端恢复历史时只拉最近一段，避免首屏越来越慢

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

### 启动后提示向量库未加载

通常说明还没有执行过知识库初始化：

```bash
cd backend
uv run python ingest.py
```

然后重启后端。

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

前端生产构建：

```bash
cd frontend
npm run build
```

## 备注

- 当前项目是“讲话 CSV 专用 RAG”，不是通用文档导入器
- 会话状态保存在本地 SQLite，适合个人部署和轻量使用
- 如果部署到公网，建议额外加认证和反向代理
