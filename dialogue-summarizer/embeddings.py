"""
Embedding向量化模块
支持Ollama本地模型和OpenAI API格式的模型
"""
import requests
from typing import List, Optional
from abc import ABC, abstractmethod
import numpy as np
from tqdm import tqdm

from config import config, OllamaConfig, OpenAIConfig


class EmbeddingModel(ABC):
    """Embedding模型基类"""
    
    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """将文本列表转换为向量"""
        pass
    
    @abstractmethod
    def embed_single(self, text: str) -> List[float]:
        """将单个文本转换为向量"""
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """返回向量维度"""
        pass


class OllamaEmbedding(EmbeddingModel):
    """Ollama Embedding模型"""
    
    def __init__(self, cfg: OllamaConfig = None):
        self.cfg = cfg or config.ollama
        self.base_url = self.cfg.base_url.rstrip("/")
        self.model = self.cfg.embedding_model
        self._dimension = None
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """批量生成向量"""
        embeddings = []
        for text in tqdm(texts, desc="生成向量中"):
            embedding = self.embed_single(text)
            embeddings.append(embedding)
        return embeddings
    
    def embed_single(self, text: str) -> List[float]:
        """生成单个文本的向量"""
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.model,
            "prompt": text
        }
        
        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result.get("embedding", [])
        except Exception as e:
            print(f"Ollama embedding error: {e}")
            # 返回空向量
            return [0.0] * self.dimension
    
    @property
    def dimension(self) -> int:
        """获取向量维度"""
        if self._dimension is None:
            # 常见Ollama embedding模型的维度
            dimension_map = {
                "nomic-embed-text": 768,
                "mxbai-embed-large": 1024,
                "all-minilm": 384,
                "snowflake-arctic-embed": 1024,
            }
            self._dimension = dimension_map.get(self.model, 768)
        return self._dimension


class OpenAIEmbedding(EmbeddingModel):
    """OpenAI API Embedding模型"""
    
    def __init__(self, cfg: OpenAIConfig = None):
        self.cfg = cfg or config.openai
        self.api_key = self.cfg.api_key
        self.base_url = self.cfg.base_url.rstrip("/")
        self.model = self.cfg.embedding_model
        self._dimension = None
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """批量生成向量"""
        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        all_embeddings = []
        batch_size = 100  # OpenAI推荐的批大小
        
        for i in tqdm(range(0, len(texts), batch_size), desc="生成向量中"):
            batch = texts[i:i + batch_size]
            payload = {
                "model": self.model,
                "input": batch
            }
            
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=120)
                response.raise_for_status()
                result = response.json()
                
                # 按index排序
                embeddings_data = sorted(result.get("data", []), key=lambda x: x.get("index", 0))
                batch_embeddings = [item.get("embedding", []) for item in embeddings_data]
                all_embeddings.extend(batch_embeddings)
                
            except Exception as e:
                print(f"OpenAI embedding error: {e}")
                # 返回空向量
                all_embeddings.extend([[0.0] * self.dimension] * len(batch))
        
        return all_embeddings
    
    def embed_single(self, text: str) -> List[float]:
        """生成单个文本的向量"""
        embeddings = self.embed([text])
        return embeddings[0] if embeddings else [0.0] * self.dimension
    
    @property
    def dimension(self) -> int:
        """获取向量维度"""
        if self._dimension is None:
            dimension_map = {
                "text-embedding-3-small": 1536,
                "text-embedding-3-large": 3072,
                "text-embedding-ada-002": 1536,
            }
            self._dimension = dimension_map.get(self.model, 1536)
        return self._dimension


class SentenceTransformerEmbedding(EmbeddingModel):
    """Sentence-Transformers本地Embedding模型"""
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model_name = model_name
        self._model = None
        self._dimension = None
    
    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """批量生成向量"""
        embeddings = self.model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
        return embeddings.tolist()
    
    def embed_single(self, text: str) -> List[float]:
        """生成单个文本的向量"""
        embedding = self.model.encode([text], convert_to_numpy=True)
        return embedding[0].tolist()
    
    @property
    def dimension(self) -> int:
        """获取向量维度"""
        if self._dimension is None:
            self._dimension = self.model.get_sentence_embedding_dimension()
        return self._dimension


def get_embedding_model(backend: str = None, **kwargs) -> EmbeddingModel:
    """获取Embedding模型实例"""
    backend = backend or config.backend
    
    if backend == "ollama":
        return OllamaEmbedding(**kwargs)
    elif backend == "openai":
        return OpenAIEmbedding(**kwargs)
    elif backend == "sentence-transformers":
        return SentenceTransformerEmbedding(**kwargs)
    else:
        raise ValueError(f"Unsupported backend: {backend}")


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """计算余弦相似度"""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def rerank_by_similarity(query_embedding: List[float], 
                         documents: List[Dict], 
                         doc_embeddings: List[List[float]],
                         top_k: int = 5) -> List[Dict]:
    """基于余弦相似度重排序"""
    scores = []
    for i, doc_emb in enumerate(doc_embeddings):
        score = cosine_similarity(query_embedding, doc_emb)
        scores.append((i, score))
    
    # 按分数降序排序
    scores.sort(key=lambda x: x[1], reverse=True)
    
    # 返回top-k结果
    results = []
    for idx, score in scores[:top_k]:
        doc = documents[idx].copy()
        doc["score"] = score
        results.append(doc)
    
    return results
