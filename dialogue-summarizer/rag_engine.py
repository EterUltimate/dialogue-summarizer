"""
RAG检索引擎模块
整合向量存储和检索逻辑
"""
import os
import json
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from config import config
from parser import DialogueParser, DialogueDocument, TextChunker
from embeddings import EmbeddingModel, get_embedding_model
from vectordb import VectorStore, get_vector_store


class RAGEngine:
    """RAG检索引擎"""
    
    def __init__(self, 
                 embedding_model: EmbeddingModel = None,
                 vector_store: VectorStore = None,
                 chunk_size: int = None,
                 chunk_overlap: int = None):
        
        self.embedding_model = embedding_model or get_embedding_model()
        self.vector_store = vector_store or get_vector_store(embedding_model=self.embedding_model)
        self.parser = DialogueParser()
        self.chunker = TextChunker(
            chunk_size=chunk_size or config.chunk_size,
            overlap=chunk_overlap or config.chunk_overlap
        )
        
        self._current_document: Optional[DialogueDocument] = None
        self._is_indexed = False
    
    def index_document(self, file_path: str) -> Dict[str, Any]:
        """索引文档"""
        # 解析文档
        self._current_document = self.parser.parse_file(file_path)
        
        # 分块
        chunks = self.chunker.chunk_document(self._current_document)
        
        if not chunks:
            return {"status": "error", "message": "没有可索引的内容"}
        
        # 生成向量
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedding_model.embed(texts)
        
        # 添加到向量存储
        ids = [chunk["id"] for chunk in chunks]
        documents = [{"text": chunk["text"], "metadata": chunk["metadata"]} for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        
        # 清除旧数据
        if self.vector_store.count() > 0:
            self.vector_store.delete()
        
        self.vector_store.add(ids, embeddings, documents, metadatas)
        self.vector_store.save()
        
        self._is_indexed = True
        
        return {
            "status": "success",
            "message": f"成功索引 {len(chunks)} 个文本块",
            "document_name": self._current_document.character_name,
            "total_nodes": len(self._current_document.nodes),
            "total_events": len(self._current_document.memory_events)
        }
    
    def index_json_data(self, data: Dict) -> Dict[str, Any]:
        """直接索引JSON数据"""
        self._current_document = self.parser.parse(data)
        
        chunks = self.chunker.chunk_document(self._current_document)
        
        if not chunks:
            return {"status": "error", "message": "没有可索引的内容"}
        
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedding_model.embed(texts)
        
        ids = [chunk["id"] for chunk in chunks]
        documents = [{"text": chunk["text"], "metadata": chunk["metadata"]} for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        
        if self.vector_store.count() > 0:
            self.vector_store.delete()
        
        self.vector_store.add(ids, embeddings, documents, metadatas)
        self.vector_store.save()
        
        self._is_indexed = True
        
        return {
            "status": "success",
            "message": f"成功索引 {len(chunks)} 个文本块",
            "document_name": self._current_document.character_name,
            "total_nodes": len(self._current_document.nodes),
            "total_events": len(self._current_document.memory_events)
        }
    
    def search(self, query: str, top_k: int = None) -> List[Dict]:
        """搜索相关内容"""
        if not self._is_indexed and self.vector_store.count() == 0:
            return []
        
        # 生成查询向量
        query_embedding = self.embedding_model.embed_single(query)
        
        # 搜索
        top_k = top_k or config.top_k
        results = self.vector_store.search(query_embedding, top_k)
        
        return results
    
    def get_context(self, query: str, top_k: int = None) -> str:
        """获取检索上下文"""
        results = self.search(query, top_k)
        
        if not results:
            return ""
        
        context_parts = []
        for i, result in enumerate(results, 1):
            source = result.get("metadata", {}).get("source", "未知来源")
            text = result.get("text", "")
            score = result.get("score", result.get("distance", 0))
            
            context_parts.append(f"[相关片段 {i}] (来源: {source}, 相关度: {score:.3f})\n{text}")
        
        return "\n\n".join(context_parts)
    
    def get_all_text(self) -> str:
        """获取所有文本内容"""
        if self._current_document:
            return self._current_document.get_all_text()
        return ""
    
    def get_document_info(self) -> Dict:
        """获取文档信息"""
        if not self._current_document:
            return {}
        
        return {
            "character_name": self._current_document.character_name,
            "export_date": self._current_document.export_date,
            "total_nodes": len(self._current_document.nodes),
            "total_events": len(self._current_document.memory_events),
            "is_indexed": self._is_indexed,
            "vector_count": self.vector_store.count()
        }
    
    def export_summary_text(self, output_path: str = None) -> str:
        """导出纯文本总结"""
        if not self._current_document:
            return ""
        
        text = self._current_document.get_all_text()
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
        
        return text
    
    def clear(self):
        """清除所有数据"""
        if self.vector_store.count() > 0:
            self.vector_store.delete()
            self.vector_store.save()
        
        self._current_document = None
        self._is_indexed = False


class Reranker:
    """重排序器"""
    
    def __init__(self, model_name: str = None, backend: str = None):
        self.model_name = model_name
        self.backend = backend or config.backend
        self._model = None
    
    def rerank(self, query: str, documents: List[Dict], top_k: int = 5) -> List[Dict]:
        """重排序文档"""
        if self.backend == "ollama" and config.ollama.rerank_model:
            return self._rerank_with_ollama(query, documents, top_k)
        else:
            # 使用简单的相似度重排序
            return self._rerank_by_similarity(query, documents, top_k)
    
    def _rerank_with_ollama(self, query: str, documents: List[Dict], top_k: int) -> List[Dict]:
        """使用Ollama进行重排序"""
        # 这里可以实现更复杂的重排序逻辑
        # 例如使用LLM对每个文档进行评分
        return documents[:top_k]
    
    def _rerank_by_similarity(self, query: str, documents: List[Dict], top_k: int) -> List[Dict]:
        """基于相似度重排序"""
        # 文档已经按相似度排序了
        return documents[:top_k]
