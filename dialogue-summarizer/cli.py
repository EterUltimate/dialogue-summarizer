#!/usr/bin/env python3
"""
命令行接口
用于快速使用对话总结功能
"""
import argparse
import os
import sys

from config import config
from embeddings import get_embedding_model
from vectordb import get_vector_store
from rag_engine import RAGEngine
from summarizer import Summarizer, get_llm


def main():
    parser = argparse.ArgumentParser(
        description="角色扮演对话总结系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 加载文件并生成全面总结
  python cli.py -f dialogue.json --summarize
  
  # 搜索特定内容
  python cli.py -f dialogue.json --search "小兔"
  
  # 生成时间线
  python cli.py -f dialogue.json --timeline
  
  # 导出纯文本
  python cli.py -f dialogue.json --export output.txt
        """
    )
    
    parser.add_argument("-f", "--file", required=True, help="对话JSON文件路径")
    parser.add_argument("--backend", choices=["ollama", "openai"], 
                        default=config.backend, help="使用的后端")
    
    # 操作选项
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--summarize", action="store_true", help="生成总结")
    action.add_argument("--search", metavar="QUERY", help="搜索内容")
    action.add_argument("--timeline", action="store_true", help="生成时间线")
    action.add_argument("--character", metavar="NAME", nargs="?", const="", 
                        help="生成角色分析")
    action.add_argument("--export", metavar="OUTPUT", help="导出纯文本")
    action.add_argument("--info", action="store_true", help="显示文件信息")
    
    # 总结选项
    parser.add_argument("--focus", choices=["全面", "角色", "剧情", "情感"],
                        default="全面", help="总结聚焦方向")
    parser.add_argument("--style", choices=["详细", "简洁", "要点"],
                        default="详细", help="总结风格")
    parser.add_argument("--top-k", type=int, default=5, help="检索深度")
    
    args = parser.parse_args()
    
    # 初始化引擎
    print(f"使用后端: {args.backend}")
    print("初始化引擎...")
    
    embedding_model = get_embedding_model(args.backend)
    vector_store = get_vector_store(embedding_model=embedding_model)
    rag_engine = RAGEngine(embedding_model, vector_store)
    llm = get_llm(args.backend)
    summarizer = Summarizer(rag_engine, llm)
    
    # 加载文件
    print(f"加载文件: {args.file}")
    result = rag_engine.index_document(args.file)
    
    if result["status"] != "success":
        print(f"加载失败: {result['message']}")
        sys.exit(1)
    
    print(result["message"])
    
    # 执行操作
    if args.info:
        info = rag_engine.get_document_info()
        print("\n=== 文件信息 ===")
        for key, value in info.items():
            print(f"{key}: {value}")
    
    elif args.summarize:
        print(f"\n生成总结中... (聚焦: {args.focus}, 风格: {args.style})")
        summary = summarizer.summarize(
            query=None,
            focus=args.focus,
            style=args.style,
            top_k=args.top_k
        )
        print("\n" + "="*50)
        print(summary)
    
    elif args.search:
        print(f"\n搜索: {args.search}")
        results = rag_engine.search(args.search, args.top_k)
        
        if not results:
            print("未找到相关内容")
        else:
            for i, r in enumerate(results, 1):
                print(f"\n--- 结果 {i} ---")
                print(f"来源: {r.get('metadata', {}).get('source', '未知')}")
                print(f"相关度: {r.get('score', 0):.3f}")
                print(f"内容:\n{r.get('text', '')}")
    
    elif args.timeline:
        print("\n生成时间线...")
        timeline = summarizer.generate_timeline()
        print("\n" + "="*50)
        print(timeline)
    
    elif args.character is not None:
        name = args.character or None
        print(f"\n生成角色分析... {name or '(默认角色)'}")
        analysis = summarizer.generate_character_analysis(name)
        print("\n" + "="*50)
        print(analysis)
    
    elif args.export:
        print(f"\n导出到: {args.export}")
        text = rag_engine.export_summary_text(args.export)
        print(f"成功导出 {len(text)} 字符")


if __name__ == "__main__":
    main()
