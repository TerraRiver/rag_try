# 知识库文档目录

将你的知识库文档放在这个目录下，支持以下格式：
- `.txt` — 纯文本
- `.md` — Markdown
- `.pdf` — PDF 文件

然后在 `backend/` 目录下运行：
```bash
python ingest.py
```

脚本会自动完成文本分块、向量化并存储到本地 ChromaDB。
