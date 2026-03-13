"""
总结生成模块
使用LLM生成对话总结
"""
import requests
import json
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from config import config, OllamaConfig, OpenAIConfig
from rag_engine import RAGEngine


class LLMBase(ABC):
    """LLM基类"""
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        """生成文本"""
        pass
    
    @abstractmethod
    def chat(self, messages: List[Dict], **kwargs) -> str:
        """对话生成"""
        pass


class OllamaLLM(LLMBase):
    """Ollama LLM"""
    
    def __init__(self, cfg: OllamaConfig = None):
        self.cfg = cfg or config.ollama
        self.base_url = self.cfg.base_url.rstrip("/")
        self.model = self.cfg.llm_model
    
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        """生成文本"""
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 4096
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            return f"生成失败: {str(e)}"
    
    def chat(self, messages: List[Dict], **kwargs) -> str:
        """对话生成"""
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 4096)
            }
        }
        
        try:
            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()
            result = response.json()
            return result.get("message", {}).get("content", "")
        except Exception as e:
            return f"生成失败: {str(e)}"


class OpenAILLM(LLMBase):
    """OpenAI API LLM"""
    
    def __init__(self, cfg: OpenAIConfig = None):
        self.cfg = cfg or config.openai
        self.api_key = self.cfg.api_key
        self.base_url = self.cfg.base_url.rstrip("/")
        self.model = self.cfg.llm_model
    
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        """生成文本"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return self.chat(messages)
    
    def chat(self, messages: List[Dict], **kwargs) -> str:
        """对话生成"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096)
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            return f"生成失败: {str(e)}"


def get_llm(backend: str = None, **kwargs) -> LLMBase:
    """获取LLM实例"""
    backend = backend or config.backend
    
    if backend == "ollama":
        return OllamaLLM(**kwargs)
    elif backend == "openai":
        return OpenAILLM(**kwargs)
    else:
        raise ValueError(f"Unsupported backend: {backend}")


class Summarizer:
    """总结生成器"""
    
    def __init__(self, rag_engine: RAGEngine = None, llm: LLMBase = None):
        self.rag_engine = rag_engine
        self.llm = llm or get_llm()
    
    def summarize(self, 
                  query: str = None, 
                  focus: str = "全面",
                  style: str = "详细",
                  top_k: int = 5) -> str:
        """
        生成总结
        
        Args:
            query: 查询关键词，如果为None则总结全部内容
            focus: 聚焦方向 (全面/角色/剧情/情感)
            style: 风格 (详细/简洁/要点)
            top_k: 检索top-k相关内容
        """
        if not self.rag_engine or not self.rag_engine._is_indexed:
            return "请先加载并索引文档"
        
        # 获取上下文
        if query:
            context = self.rag_engine.get_context(query, top_k)
            if not context:
                return "未找到相关内容"
        else:
            # 获取全部内容
            context = self.rag_engine.get_all_text()
        
        # 构建提示词
        system_prompt = self._get_system_prompt(focus, style)
        user_prompt = self._get_user_prompt(query, context, focus, style)
        
        # 生成总结
        summary = self.llm.generate(user_prompt, system_prompt)
        
        return summary
    
    def summarize_by_topic(self, topics: List[str] = None) -> Dict[str, str]:
        """按主题生成总结"""
        if topics is None:
            topics = ["角色关系发展", "关键事件", "情感变化", "重要对话"]
        
        results = {}
        for topic in topics:
            summary = self.summarize(query=topic, focus="剧情", style="要点", top_k=3)
            results[topic] = summary
        
        return results
    
    def generate_timeline(self) -> str:
        """生成时间线总结"""
        if not self.rag_engine or not self.rag_engine._current_document:
            return "请先加载文档"
        
        events = self.rag_engine._current_document.memory_events
        if not events:
            return "没有事件记录"
        
        timeline_prompt = """根据以下事件记录，生成一个清晰的时间线总结：

事件列表：
""" + "\n".join([e.to_text() for e in events])

        system_prompt = "你是一个专业的剧情分析师，请生成清晰、有条理的时间线总结。"
        
        return self.llm.generate(timeline_prompt, system_prompt)
    
    def generate_character_analysis(self, character_name: str = None) -> str:
        """生成角色分析"""
        if not self.rag_engine or not self.rag_engine._is_indexed:
            return "请先加载并索引文档"
        
        doc_info = self.rag_engine.get_document_info()
        character = character_name or doc_info.get("character_name", "主角")
        
        # 检索角色相关内容
        context = self.rag_engine.get_context(character, top_k=10)
        
        prompt = f"""请分析角色"{character}"的性格特点、心理变化和成长轨迹。

相关内容：
{context}

请从以下几个方面进行分析：
1. 性格特点
2. 心理变化历程
3. 关键转折点
4. 与其他角色的关系
5. 成长与蜕变"""
        
        system_prompt = "你是一个专业的角色分析师，请深入分析角色的内心世界和成长轨迹。"
        
        return self.llm.generate(prompt, system_prompt)
    
    def _get_system_prompt(self, focus: str, style: str) -> str:
        """获取系统提示词"""
        base = "你是一个专业的故事总结助手，擅长分析和总结角色扮演对话内容。"
        
        focus_prompts = {
            "全面": "请从剧情、角色、情感等多个维度进行全面总结。",
            "角色": "请重点关注角色的性格特点、心理变化和成长轨迹。",
            "剧情": "请重点关注故事情节的发展脉络和关键事件。",
            "情感": "请重点关注角色之间的情感变化和关系发展。"
        }
        
        style_prompts = {
            "详细": "请提供详细的总结，包含具体的细节和引用。",
            "简洁": "请提供简洁明了的总结，突出重点。",
            "要点": "请以要点列表的形式提供总结。"
        }
        
        return f"{base}\n\n{focus_prompts.get(focus, focus_prompts['全面'])}\n{style_prompts.get(style, style_prompts['详细'])}"
    
    def _get_user_prompt(self, query: str, context: str, focus: str, style: str) -> str:
        """获取用户提示词"""
        if query:
            return f"""请根据以下相关内容，针对"{query}"生成总结：

{context}"""
        else:
            return f"""请对以下内容进行全面总结：

{context}"""


def create_summary_engine(backend: str = None) -> tuple:
    """创建总结引擎（便捷函数）"""
    from embeddings import get_embedding_model
    from vectordb import get_vector_store
    
    embedding_model = get_embedding_model(backend)
    vector_store = get_vector_store(embedding_model=embedding_model)
    rag_engine = RAGEngine(embedding_model, vector_store)
    llm = get_llm(backend)
    summarizer = Summarizer(rag_engine, llm)
    
    return rag_engine, summarizer
