"""
配置管理模块
支持从环境变量和配置文件加载配置
"""
import os
from typing import Optional, Literal
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class OllamaConfig(BaseModel):
    """Ollama配置"""
    base_url: str = Field(default="http://localhost:11434", description="Ollama服务地址")
    embedding_model: str = Field(default="nomic-embed-text", description="Embedding模型名称")
    rerank_model: Optional[str] = Field(default=None, description="Rerank模型名称（可选）")
    llm_model: str = Field(default="qwen2.5:7b", description="LLM模型名称")


class OpenAIConfig(BaseModel):
    """OpenAI API配置"""
    api_key: str = Field(default="", description="API密钥")
    base_url: str = Field(default="https://api.openai.com/v1", description="API基础URL")
    embedding_model: str = Field(default="text-embedding-3-small", description="Embedding模型")
    llm_model: str = Field(default="gpt-4o-mini", description="LLM模型")


class VectorDBConfig(BaseModel):
    """向量数据库配置"""
    type: Literal["chroma", "faiss"] = Field(default="chroma", description="向量数据库类型")
    persist_directory: str = Field(default="./data/vectordb", description="持久化目录")
    collection_name: str = Field(default="dialogue_summaries", description="集合名称")


class AppConfig(BaseModel):
    """应用总配置"""
    # 后端类型：ollama 或 openai
    backend: Literal["ollama", "openai"] = Field(
        default="ollama", 
        description="使用的后端类型"
    )
    
    # 模型配置
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    
    # 向量数据库配置
    vectordb: VectorDBConfig = Field(default_factory=VectorDBConfig)
    
    # RAG配置
    chunk_size: int = Field(default=500, description="文本块大小")
    chunk_overlap: int = Field(default=50, description="文本块重叠大小")
    top_k: int = Field(default=5, description="检索返回的top-k结果")
    
    # 应用配置
    data_dir: str = Field(default="./data", description="数据目录")
    cache_dir: str = Field(default="./cache", description="缓存目录")
    
    class Config:
        env_prefix = "DIALOGUE_"
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """从环境变量加载配置"""
        config = cls()
        
        # 后端类型
        if backend := os.getenv("DIALOGUE_BACKEND"):
            config.backend = backend
        
        # Ollama配置
        if url := os.getenv("OLLAMA_BASE_URL"):
            config.ollama.base_url = url
        if model := os.getenv("OLLAMA_EMBEDDING_MODEL"):
            config.ollama.embedding_model = model
        if model := os.getenv("OLLAMA_RERANK_MODEL"):
            config.ollama.rerank_model = model
        if model := os.getenv("OLLAMA_LLM_MODEL"):
            config.ollama.llm_model = model
        
        # OpenAI配置
        if key := os.getenv("OPENAI_API_KEY"):
            config.openai.api_key = key
        if url := os.getenv("OPENAI_BASE_URL"):
            config.openai.base_url = url
        if model := os.getenv("OPENAI_EMBEDDING_MODEL"):
            config.openai.embedding_model = model
        if model := os.getenv("OPENAI_LLM_MODEL"):
            config.openai.llm_model = model
        
        return config


# 全局配置实例
config = AppConfig.from_env()
