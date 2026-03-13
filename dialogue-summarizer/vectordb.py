"""
向量数据库存储模块
支持ChromaDB和FAISS两种后端
"""
import os
import json
import pickle
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import numpy as np

from config import config, VectorDBConfig
from embeddings import EmbeddingModel, get_embedding_model


class VectorStore(ABC):
    """向量存储基类"""
    
    @abstractmethod
    def add(self, ids: List[str], embeddings: List[List[float]], 
            documents: List[Dict], metadatas: List[Dict] = None):
        """添加向量"""
        pass
    
    @abstractmethod
    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict]:
        """搜索相似向量"""
        pass
    
    @abstractmethod
    def delete(self, ids: List[str] = None, where: Dict = None):
        """删除向量"""
        pass
    
    @abstractmethod
    def count(self) -> int:
        """返回向量数量"""
        pass
    
    @abstractmethod
    def save(self):
        """保存到磁盘"""
        pass
    
    @abstractmethod
    def load(self):
        """从磁盘加载"""
        pass


class ChromaVectorStore(VectorStore):
    """ChromaDB向量存储"""
    
    def __init__(self, cfg: VectorDBConfig = None, embedding_model: EmbeddingModel = None):
        self.cfg = cfg or config.vectordb
        self.embedding_model = embedding_model or get_embedding_model()
        
        # 确保目录存在
        os.makedirs(self.cfg.persist_directory, exist_ok=True)
        
        # 初始化ChromaDB
        import chromadb
        from chromadb.config import Settings
        
        self.client = chromadb.PersistentClient(
            path=self.cfg.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection = self.client.get_or_create_collection(
            name=self.cfg.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def add(self, ids: List[str], embeddings: List[List[float]], 
            documents: List[Dict], metadatas: List[Dict] = None):
        """添加向量"""
        texts = [doc.get("text", "") for doc in documents]
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas or [doc.get("metadata", {}) for doc in documents]
        )
    
    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict]:
        """搜索相似向量"""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        documents = []
        if results and results.get("ids"):
            for i, doc_id in enumerate(results["ids"][0]):
                documents.append({
                    "id": doc_id,
                    "text": results["documents"][0][i] if results.get("documents") else "",
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else 0.0
                })
        
        return documents
    
    def delete(self, ids: List[str] = None, where: Dict = None):
        """删除向量"""
        if ids:
            self.collection.delete(ids=ids)
        elif where:
            self.collection.delete(where=where)
    
    def count(self) -> int:
        """返回向量数量"""
        return self.collection.count()
    
    def save(self):
        """ChromaDB自动持久化"""
        pass
    
    def load(self):
        """ChromaDB自动加载"""
        pass


class FAISSVectorStore(VectorStore):
    """FAISS向量存储"""
    
    def __init__(self, cfg: VectorDBConfig = None, embedding_model: EmbeddingModel = None):
        self.cfg = cfg or config.vectordb
        self.embedding_model = embedding_model or get_embedding_model()
        
        self.index = None
        self.documents = []  # 存储文档内容
        self.id_to_idx = {}  # id到索引的映射
        
        # 确保目录存在
        os.makedirs(self.cfg.persist_directory, exist_ok=True)
        
        # 尝试加载已有索引
        self.load()
    
    def _init_index(self, dimension: int):
        """初始化FAISS索引"""
        import faiss
        
        # 使用IndexFlatIP（内积）配合归一化向量实现余弦相似度
        self.index = faiss.IndexFlatIP(dimension)
        # 或者使用IndexIVFFlat进行近似搜索（适合大规模数据）
        # quantizer = faiss.IndexFlatIP(dimension)
        # self.index = faiss.IndexIVFFlat(quantizer, dimension, 100)
    
    def add(self, ids: List[str], embeddings: List[List[float]], 
            documents: List[Dict], metadatas: List[Dict] = None):
        """添加向量"""
        import faiss
        
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        # 归一化向量（用于余弦相似度）
        faiss.normalize_L2(embeddings_array)
        
        if self.index is None:
            self._init_index(embeddings_array.shape[1])
        
        # 添加到索引
        start_idx = len(self.documents)
        self.index.add(embeddings_array)
        
        # 存储文档
        for i, (doc_id, doc) in enumerate(zip(ids, documents)):
            idx = start_idx + i
            self.documents.append({
                "id": doc_id,
                "text": doc.get("text", ""),
                "metadata": metadatas[i] if metadatas else doc.get("metadata", {})
            })
            self.id_to_idx[doc_id] = idx
    
    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict]:
        """搜索相似向量"""
        import faiss
        
        if self.index is None or self.index.ntotal == 0:
            return []
        
        query_array = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_array)
        
        # 搜索
        distances, indices = self.index.search(query_array, min(top_k, self.index.ntotal))
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.documents):
                doc = self.documents[idx].copy()
                doc["score"] = float(distances[0][i])
                results.append(doc)
        
        return results
    
    def delete(self, ids: List[str] = None, where: Dict = None):
        """删除向量（FAISS不支持直接删除，需要重建索引）"""
        if ids:
            # 标记为删除
            indices_to_remove = [self.id_to_idx.get(id_) for id_ in ids if id_ in self.id_to_idx]
            # 简单实现：重建索引
            # TODO: 更高效的实现
            pass
    
    def count(self) -> int:
        """返回向量数量"""
        return len(self.documents)
    
    def save(self):
        """保存到磁盘"""
        import faiss
        
        if self.index is None:
            return
        
        index_path = os.path.join(self.cfg.persist_directory, "faiss_index.bin")
        docs_path = os.path.join(self.cfg.persist_directory, "documents.pkl")
        
        faiss.write_index(self.index, index_path)
        
        with open(docs_path, 'wb') as f:
            pickle.dump({
                "documents": self.documents,
                "id_to_idx": self.id_to_idx
            }, f)
    
    def load(self):
        """从磁盘加载"""
        import faiss
        
        index_path = os.path.join(self.cfg.persist_directory, "faiss_index.bin")
        docs_path = os.path.join(self.cfg.persist_directory, "documents.pkl")
        
        if os.path.exists(index_path) and os.path.exists(docs_path):
            self.index = faiss.read_index(index_path)
            
            with open(docs_path, 'rb') as f:
                data = pickle.load(f)
                self.documents = data.get("documents", [])
                self.id_to_idx = data.get("id_to_idx", {})


class SimpleVectorStore(VectorStore):
    """简单的内存向量存储（无需额外依赖）"""
    
    def __init__(self, cfg: VectorDBConfig = None):
        self.cfg = cfg or config.vectordb
        self.embeddings = []
        self.documents = []
        self.id_to_idx = {}
        
        os.makedirs(self.cfg.persist_directory, exist_ok=True)
        self.load()
    
    def add(self, ids: List[str], embeddings: List[List[float]], 
            documents: List[Dict], metadatas: List[Dict] = None):
        """添加向量"""
        start_idx = len(self.documents)
        
        for i, (doc_id, emb, doc) in enumerate(zip(ids, embeddings, documents)):
            idx = start_idx + i
            self.embeddings.append(emb)
            self.documents.append({
                "id": doc_id,
                "text": doc.get("text", ""),
                "metadata": metadatas[i] if metadatas else doc.get("metadata", {})
            })
            self.id_to_idx[doc_id] = idx
    
    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict]:
        """搜索相似向量（使用余弦相似度）"""
        if not self.embeddings:
            return []
        
        from embeddings import cosine_similarity
        
        scores = []
        for i, emb in enumerate(self.embeddings):
            score = cosine_similarity(query_embedding, emb)
            scores.append((i, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for idx, score in scores[:top_k]:
            doc = self.documents[idx].copy()
            doc["score"] = score
            results.append(doc)
        
        return results
    
    def delete(self, ids: List[str] = None, where: Dict = None):
        """删除向量"""
        if ids:
            indices_to_remove = sorted([self.id_to_idx.get(id_) for id_ in ids if id_ in self.id_to_idx], reverse=True)
            for idx in indices_to_remove:
                if idx is not None:
                    self.embeddings.pop(idx)
                    self.documents.pop(idx)
    
    def count(self) -> int:
        """返回向量数量"""
        return len(self.documents)
    
    def save(self):
        """保存到磁盘"""
        data_path = os.path.join(self.cfg.persist_directory, "store.pkl")
        
        with open(data_path, 'wb') as f:
            pickle.dump({
                "embeddings": self.embeddings,
                "documents": self.documents,
                "id_to_idx": self.id_to_idx
            }, f)
    
    def load(self):
        """从磁盘加载"""
        data_path = os.path.join(self.cfg.persist_directory, "store.pkl")
        
        if os.path.exists(data_path):
            with open(data_path, 'rb') as f:
                data = pickle.load(f)
                self.embeddings = data.get("embeddings", [])
                self.documents = data.get("documents", [])
                self.id_to_idx = data.get("id_to_idx", {})


def get_vector_store(store_type: str = None, embedding_model: EmbeddingModel = None, **kwargs) -> VectorStore:
    """获取向量存储实例"""
    store_type = store_type or config.vectordb.type
    
    if store_type == "chroma":
        return ChromaVectorStore(embedding_model=embedding_model, **kwargs)
    elif store_type == "faiss":
        return FAISSVectorStore(embedding_model=embedding_model, **kwargs)
    elif store_type == "simple":
        return SimpleVectorStore(**kwargs)
    else:
        raise ValueError(f"Unsupported vector store type: {store_type}")
