# 知识库数据目录

当前项目的 `ingest.py` 只读取这个目录下的 CSV 文件：

- `contentALL1-12298.csv`

CSV 预期字段为：

- `原序号`
- `标题`
- `来源`
- `时间`
- `内容`
- `原文刊登`
- `链接`
- `类型`

在 `backend/` 目录下运行：

```bash
uv run python ingest.py
```

脚本会读取上述 CSV，完成文本分块、向量化，并将结果写入本地 ChromaDB。
