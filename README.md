# 角色扮演对话总结系统

基于RAG（检索增强生成）技术的本地对话总结应用，支持AI角色扮演网站的对话记录分析和总结。

## 功能特点

- 📁 **JSON解析**：自动解析角色扮演对话JSON格式
- 🔍 **智能检索**：基于向量相似度的语义检索
- 📝 **AI总结**：支持多种总结风格和聚焦方向
- 📊 **专项分析**：时间线梳理、角色分析等
- 💾 **纯文本导出**：一键导出完整对话记录
- 🏠 **完全本地**：支持Ollama本地模型，无需联网

## 快速开始

### 1. 安装依赖

```bash
cd dialogue-summarizer
pip install -r requirements.txt
```

### 2. 配置环境

复制配置文件并修改：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置你的模型：

**使用Ollama（推荐）：**
```env
DIALOGUE_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_LLM_MODEL=qwen2.5:7b
```

**使用OpenAI API：**
```env
DIALOGUE_BACKEND=openai
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 3. 启动应用

```bash
python app.py
```

访问 http://localhost:7860 使用Web界面。

## 支持的后端

### Ollama（本地）

需要先安装并运行Ollama：

```bash
# 安装Ollama（参考 https://ollama.ai）

# 拉取模型
ollama pull nomic-embed-text  # Embedding模型
ollama pull qwen2.5:7b        # LLM模型
```

**推荐的Embedding模型：**
- `nomic-embed-text` - 平衡性能和质量
- `mxbai-embed-large` - 更高质量
- `all-minilm` - 轻量级

**推荐的LLM模型：**
- `qwen2.5:7b` - 中文友好
- `llama3.1:8b` - 通用性强
- `mistral:7b` - 效率高

### OpenAI API

支持标准OpenAI API格式，可以使用：
- 官方OpenAI API
- Azure OpenAI
- 第三方兼容API（如DeepSeek、智谱等）

## 使用指南

### 加载文件

1. 在"文件加载"标签页选择JSON文件
2. 点击"加载文件"
3. 系统会自动解析并建立向量索引

### 内容检索

1. 切换到"内容检索"标签
2. 输入搜索关键词
3. 调整返回结果数量
4. 点击搜索查看相关内容

### 智能总结

1. 切换到"智能总结"标签
2. （可选）输入总结重点
3. 选择聚焦方向：
   - **全面**：多维度综合总结
   - **角色**：侧重角色分析
   - **剧情**：侧重故事发展
   - **情感**：侧重情感变化
4. 选择总结风格：
   - **详细**：包含具体细节
   - **简洁**：突出重点
   - **要点**：列表形式
5. 点击生成

### 专项分析

- **时间线**：梳理事件发生顺序
- **角色分析**：深入分析角色性格和心理

### 导出

点击导出可下载纯文本格式的对话记录。

## 项目结构

```
dialogue-summarizer/
├── app.py              # Gradio Web界面
├── config.py           # 配置管理
├── parser.py           # JSON解析和文本预处理
├── embeddings.py       # Embedding向量化
├── vectordb.py         # 向量数据库存储
├── rag_engine.py       # RAG检索引擎
├── summarizer.py       # 总结生成
├── requirements.txt    # Python依赖
├── .env.example        # 配置示例
└── README.md           # 说明文档
```

## 向量数据库选项

- **ChromaDB**（推荐）：功能完整，支持持久化
- **FAISS**：高性能，适合大规模数据
- **Simple**：纯Python实现，无额外依赖

在 `.env` 中设置 `VECTORDB_TYPE` 选择。

## API使用示例

也可以直接调用模块：

```python
from embeddings import get_embedding_model
from vectordb import get_vector_store
from rag_engine import RAGEngine
from summarizer import Summarizer, get_llm

# 初始化
embedding_model = get_embedding_model()
vector_store = get_vector_store(embedding_model=embedding_model)
rag_engine = RAGEngine(embedding_model, vector_store)
llm = get_llm()
summarizer = Summarizer(rag_engine, llm)

# 加载文件
rag_engine.index_document("your_dialogue.json")

# 搜索
results = rag_engine.search("关键词", top_k=5)

# 生成总结
summary = summarizer.summarize(
    query="重点内容",
    focus="剧情",
    style="详细"
)

# 导出文本
text = rag_engine.export_summary_text("output.txt")
```

## 常见问题

**Q: Ollama连接失败怎么办？**
A: 确保Ollama服务正在运行，检查 `OLLAMA_BASE_URL` 配置。

**Q: 内存不足怎么办？**
A: 尝试使用更小的模型，或使用FAISS向量数据库。

**Q: 总结质量不好？**
A: 尝试使用更大的LLM模型，或调整检索深度(top_k)。

## License

MIT
