# 领导人讲话 RAG 问答平台

基于 LangChain + ChromaDB + 硅基流动的本地知识库问答系统，前端 React，后端 FastAPI。

## 技术栈

| 层级               | 技术                           |
| ------------------ | ------------------------------ |
| 前端               | React 18 + Vite + Tailwind CSS |
| 后端               | Python + FastAPI + LangChain   |
| 向量库             | ChromaDB（本地持久化）         |
| 大模型 / Embedding | 硅基流动（OpenAI 兼容 API）    |
| 包管理             | uv（后端）/ npm（前端）        |

## 项目结构

```
rag_try/
├── .env                        # API Key、端口、模型等配置（不入库）
├── backend/
│   ├── pyproject.toml          # uv 依赖声明
│   ├── uv.lock                 # 依赖锁定文件
│   ├── main.py                 # FastAPI 入口
│   ├── rag.py                  # RAG 检索与生成逻辑
│   ├── ingest.py               # 知识库初始化脚本（离线执行一次）
│   └── docs/
│       └── contentALL1-12298.csv   # 知识库原始数据
└── frontend/
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx
        └── components/
            ├── ChatContainer.jsx
            ├── MessageList.jsx
            ├── MessageBubble.jsx
            └── ChatInput.jsx
```

---

## 部署步骤

### 前置条件

- Python >= 3.10
- Node.js >= 18
- [uv](https://docs.astral.sh/uv/) 已安装（`pip install uv` 或见官方文档）
- 硅基流动账号及 API Key（[cloud.siliconflow.cn](https://cloud.siliconflow.cn)）

---

### 第一步：配置环境变量

复制并编辑根目录的 `.env`，填入你的真实 API Key：

```
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1

LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
EMBEDDING_MODEL=BAAI/bge-m3

BACKEND_PORT=8000
CHROMA_DB_PATH=./chroma_db
DOCS_PATH=./docs
```

> 硅基流动支持的模型列表见 [文档](https://docs.siliconflow.cn/docs/getting-started)。
> LLM 也可换为 `deepseek-ai/DeepSeek-V3` 等性能更强的模型。

---

### 第二步：安装后端依赖

```bash
cd backend
uv sync
```

`uv sync` 会自动读取 `pyproject.toml`，创建 `.venv` 虚拟环境并安装所有依赖，无需手动激活。

---

### 第三步：初始化知识库（仅需执行一次）

```bash
# 仍在 backend/ 目录下
uv run python ingest.py
```

脚本会：

1. 读取 `docs/contentALL1-12298.csv`（utf-8-sig 编码）
2. 按讲话条目分块（短文整条保留，长文按中文句子边界切分，chunk_size=600）
3. 每个 chunk 头部注入【标题】【时间】【来源】作为语义锚点
4. 调用硅基流动 Embedding API 向量化，分批写入本地 ChromaDB

完成后会在 `backend/chroma_db/` 生成向量库文件。

> 数据规模：12,298 条讲话，约生成 1.5 万个 chunk，需消耗一定 Embedding API 额度，请确保账号余额充足。

---

### 第四步：启动后端

```bash
# 在 backend/ 目录下
uv run python main.py
```

启动成功后输出：

```
✅ 向量库加载成功
INFO:     Uvicorn running on http://0.0.0.0:8000
```

接口文档可访问：[http://localhost:8000/docs](http://localhost:8000/docs)

---

### 第五步：启动前端

另开一个终端：

```bash
cd frontend
npm install
npm run dev
```

启动成功后访问：[http://localhost:5173](http://localhost:5173)

> 前端开发服务器通过 Vite 代理将 `/api` 请求转发到 `http://localhost:8000`，无需额外配置跨域。

---

## API 说明

### `POST /api/chat`

**请求体**

```json
{
  "query": "习近平在哪些场合提到了人类命运共同体？",
  "history": [
    { "role": "user", "content": "上一轮问题" },
    { "role": "assistant", "content": "上一轮回答" }
  ]
}
```

`history` 为可选字段，传入后支持多轮对话上下文。

**响应体**

```json
{
  "answer": "根据知识库中的相关讲话…",
  "source_nodes": [
    "《习近平在联合国成立75周年纪念峰会上的讲话》（第1/2段）\n📰 人民网-人民日报 · 2020-09-22\n🔗 http://…\n习近平指出，面对…"
  ]
}
```

---

## 日常开发

### 后端新增依赖

```bash
cd backend
uv add <package-name>    # 自动更新 pyproject.toml 和 uv.lock
```

### 重建向量库

如需更换数据集或修改分块参数，删除旧的向量库目录后重新运行 ingest：

```bash
rm -rf backend/chroma_db
cd backend && uv run python ingest.py
```
