"""
对话总结应用 - Web界面
使用Gradio构建用户界面
"""
import os
import json
import gradio as gr
from typing import Optional

from config import config
from embeddings import get_embedding_model
from vectordb import get_vector_store
from rag_engine import RAGEngine
from summarizer import Summarizer, get_llm, create_summary_engine


class DialogueSummarizerApp:
    """对话总结应用"""
    
    def __init__(self):
        self.rag_engine: Optional[RAGEngine] = None
        self.summarizer: Optional[Summarizer] = None
        self.current_file = None
        self._init_engines()
    
    def _init_engines(self):
        """初始化引擎"""
        try:
            embedding_model = get_embedding_model()
            vector_store = get_vector_store(embedding_model=embedding_model)
            self.rag_engine = RAGEngine(embedding_model, vector_store)
            llm = get_llm()
            self.summarizer = Summarizer(self.rag_engine, llm)
        except Exception as e:
            print(f"初始化引擎失败: {e}")
    
    def load_file(self, file):
        """加载JSON文件"""
        if file is None:
            return "请选择文件"
        
        try:
            self.current_file = file.name
            result = self.rag_engine.index_document(file.name)
            
            if result["status"] == "success":
                info = self.rag_engine.get_document_info()
                return f"""✅ 加载成功！

角色名称：{info['character_name']}
导出时间：{info['export_date']}
对话节点数：{info['total_nodes']}
事件记录数：{info['total_events']}
索引文本块：{result['message']}"""
            else:
                return f"❌ 加载失败：{result['message']}"
        except Exception as e:
            return f"❌ 加载出错：{str(e)}"
    
    def search_content(self, query, top_k):
        """搜索内容"""
        if not self.rag_engine._is_indexed:
            return "请先加载文档"
        
        if not query.strip():
            return "请输入搜索内容"
        
        try:
            results = self.rag_engine.search(query, int(top_k))
            
            if not results:
                return "未找到相关内容"
            
            output = []
            for i, r in enumerate(results, 1):
                source = r.get("metadata", {}).get("source", "未知")
                score = r.get("score", 0)
                text = r.get("text", "")
                
                output.append(f"### 结果 {i} (来源: {source}, 相关度: {score:.3f})\n\n{text}\n")
            
            return "\n---\n".join(output)
        except Exception as e:
            return f"搜索出错：{str(e)}"
    
    def generate_summary(self, query, focus, style, top_k):
        """生成总结"""
        if not self.summarizer:
            return "引擎未初始化"
        
        try:
            summary = self.summarizer.summarize(
                query=query if query.strip() else None,
                focus=focus,
                style=style,
                top_k=int(top_k)
            )
            return summary
        except Exception as e:
            return f"生成出错：{str(e)}"
    
    def generate_timeline(self):
        """生成时间线"""
        if not self.summarizer:
            return "引擎未初始化"
        
        try:
            return self.summarizer.generate_timeline()
        except Exception as e:
            return f"生成出错：{str(e)}"
    
    def generate_character_analysis(self, character_name):
        """生成角色分析"""
        if not self.summarizer:
            return "引擎未初始化"
        
        try:
            name = character_name.strip() if character_name.strip() else None
            return self.summarizer.generate_character_analysis(name)
        except Exception as e:
            return f"生成出错：{str(e)}"
    
    def export_text(self):
        """导出纯文本"""
        if not self.rag_engine._current_document:
            return None, "请先加载文档"
        
        try:
            text = self.rag_engine.export_summary_text()
            
            # 保存到临时文件
            output_path = os.path.join(config.data_dir, "export_summary.txt")
            os.makedirs(config.data_dir, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            return output_path, f"✅ 已导出到: {output_path}"
        except Exception as e:
            return None, f"导出出错：{str(e)}"


def create_ui():
    """创建Gradio界面"""
    app = DialogueSummarizerApp()
    
    with gr.Blocks(title="对话总结系统", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 📖 角色扮演对话总结系统")
        gr.Markdown("使用RAG技术智能总结和分析角色扮演对话记录")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 配置信息")
                config_info = gr.Textbox(
                    label="当前配置",
                    value=f"""后端: {config.backend}
Embedding模型: {config.ollama.embedding_model if config.backend == 'ollama' else config.openai.embedding_model}
LLM模型: {config.ollama.llm_model if config.backend == 'ollama' else config.openai.llm_model}
向量数据库: {config.vectordb.type}""",
                    interactive=False
                )
        
        with gr.Tabs():
            # Tab 1: 文件加载
            with gr.TabItem("📁 文件加载"):
                with gr.Row():
                    file_input = gr.File(
                        label="选择JSON对话文件",
                        file_types=[".json"]
                    )
                load_output = gr.Textbox(
                    label="加载状态",
                    lines=5,
                    interactive=False
                )
                load_btn = gr.Button("📂 加载文件", variant="primary")
                load_btn.click(app.load_file, inputs=[file_input], outputs=[load_output])
            
            # Tab 2: 内容检索
            with gr.TabItem("🔍 内容检索"):
                with gr.Row():
                    search_input = gr.Textbox(
                        label="搜索关键词",
                        placeholder="输入要搜索的内容..."
                    )
                    search_topk = gr.Slider(
                        label="返回结果数",
                        minimum=1,
                        maximum=10,
                        value=5,
                        step=1
                    )
                search_output = gr.Markdown(label="搜索结果")
                search_btn = gr.Button("🔍 搜索", variant="primary")
                search_btn.click(
                    app.search_content,
                    inputs=[search_input, search_topk],
                    outputs=[search_output]
                )
            
            # Tab 3: 智能总结
            with gr.TabItem("📝 智能总结"):
                with gr.Row():
                    with gr.Column(scale=2):
                        summary_query = gr.Textbox(
                            label="总结重点（可选）",
                            placeholder="留空则总结全部内容，或输入特定主题..."
                        )
                    with gr.Column(scale=1):
                        summary_focus = gr.Dropdown(
                            label="聚焦方向",
                            choices=["全面", "角色", "剧情", "情感"],
                            value="全面"
                        )
                        summary_style = gr.Dropdown(
                            label="总结风格",
                            choices=["详细", "简洁", "要点"],
                            value="详细"
                        )
                        summary_topk = gr.Slider(
                            label="检索深度",
                            minimum=1,
                            maximum=10,
                            value=5,
                            step=1
                        )
                
                summary_output = gr.Textbox(
                    label="总结结果",
                    lines=15,
                    interactive=False
                )
                
                with gr.Row():
                    summary_btn = gr.Button("✨ 生成总结", variant="primary", scale=2)
                    clear_btn = gr.Button("🗑️ 清空", scale=1)
                
                summary_btn.click(
                    app.generate_summary,
                    inputs=[summary_query, summary_focus, summary_style, summary_topk],
                    outputs=[summary_output]
                )
                clear_btn.click(lambda: "", outputs=[summary_output])
            
            # Tab 4: 专项分析
            with gr.TabItem("📊 专项分析"):
                with gr.Tabs():
                    with gr.TabItem("时间线"):
                        timeline_output = gr.Textbox(
                            label="时间线总结",
                            lines=15,
                            interactive=False
                        )
                        timeline_btn = gr.Button("📅 生成时间线", variant="primary")
                        timeline_btn.click(app.generate_timeline, outputs=[timeline_output])
                    
                    with gr.TabItem("角色分析"):
                        character_input = gr.Textbox(
                            label="角色名称（留空使用默认角色）",
                            placeholder="输入角色名称..."
                        )
                        character_output = gr.Textbox(
                            label="角色分析",
                            lines=15,
                            interactive=False
                        )
                        character_btn = gr.Button("👤 生成分析", variant="primary")
                        character_btn.click(
                            app.generate_character_analysis,
                            inputs=[character_input],
                            outputs=[character_output]
                        )
            
            # Tab 5: 导出
            with gr.TabItem("💾 导出"):
                with gr.Row():
                    export_status = gr.Textbox(
                        label="导出状态",
                        interactive=False
                    )
                export_file = gr.File(label="导出文件")
                export_btn = gr.Button("📥 导出纯文本", variant="primary")
                export_btn.click(
                    app.export_text,
                    outputs=[export_file, export_status]
                )
    
    return demo


def main():
    """主函数"""
    # 确保目录存在
    os.makedirs(config.data_dir, exist_ok=True)
    os.makedirs(config.cache_dir, exist_ok=True)
    os.makedirs(config.vectordb.persist_directory, exist_ok=True)
    
    # 创建并启动界面
    demo = create_ui()
    
    print(f"""
╔══════════════════════════════════════════╗
║     角色扮演对话总结系统                    ║
╠══════════════════════════════════════════╣
║  后端: {config.backend:<35} ║
║  Embedding: {config.ollama.embedding_model if config.backend == 'ollama' else config.openai.embedding_model:<30} ║
║  LLM: {config.ollama.llm_model if config.backend == 'ollama' else config.openai.llm_model:<34} ║
╚══════════════════════════════════════════╝
    """)
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )


if __name__ == "__main__":
    main()
