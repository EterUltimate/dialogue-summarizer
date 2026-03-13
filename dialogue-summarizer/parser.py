"""
JSON解析和文本预处理模块
用于解析角色扮演对话JSON文件并提取关键信息
"""
import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DialogueNode:
    """对话节点"""
    node_id: str
    parent_node_id: Optional[str]
    user_input: str
    assistant_response: str
    full_response: str
    parsed_content: Optional[Dict] = None
    memory_snapshot: Optional[Dict] = None
    
    def to_text(self) -> str:
        """转换为纯文本格式"""
        text_parts = []
        
        # 用户输入
        if self.user_input:
            clean_input = self._clean_text(self.user_input)
            text_parts.append(f"[用户指令]\n{clean_input}")
        
        # 助手响应（提取关键内容）
        if self.assistant_response:
            clean_response = self._extract_readable_content(self.assistant_response)
            text_parts.append(f"[AI响应]\n{clean_response}")
        
        return "\n\n".join(text_parts)
    
    def _clean_text(self, text: str) -> str:
        """清理文本，移除XML标签"""
        # 移除input_message标签
        text = re.sub(r'<input_message>\s*|\s*</input_message>', '', text)
        # 移除多余空白
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()
    
    def _extract_readable_content(self, text: str) -> str:
        """提取可读内容"""
        # 提取对话
        dialogues = re.findall(r'<dialogue>(.*?)</dialogue>', text, re.DOTALL)
        # 提取叙述
        narrations = re.findall(r'<narration>(.*?)</narration>', text, re.DOTALL)
        # 提取思考
        thoughts = re.findall(r'<thought>(.*?)</thought>', text, re.DOTALL)
        
        parts = []
        if narrations:
            parts.append("[场景叙述]\n" + "\n".join(n.strip() for n in narrations if n.strip()))
        if dialogues:
            parts.append("[对话]\n" + "\n".join(d.strip() for d in dialogues if d.strip()))
        if thoughts:
            parts.append("[心理活动]\n" + "\n".join(t.strip() for t in thoughts if t.strip()))
        
        if parts:
            return "\n\n".join(parts)
        
        # 如果没有提取到结构化内容，返回清理后的原文
        return self._clean_text(text)


@dataclass
class MemoryEvent:
    """记忆事件"""
    character: str
    event_summary: str
    date: str
    location: str
    emotion: str
    
    def to_text(self) -> str:
        """转换为文本"""
        return f"【{self.date}】{self.character}在{self.location}：{self.event_summary}（情绪：{self.emotion}）"


@dataclass
class DialogueDocument:
    """对话文档"""
    export_version: str
    export_date: str
    character_name: str
    nodes: List[DialogueNode] = field(default_factory=list)
    memory_events: List[MemoryEvent] = field(default_factory=list)
    
    def get_all_text(self) -> str:
        """获取所有文本"""
        texts = []
        texts.append(f"角色扮演：{self.character_name}")
        texts.append(f"导出时间：{self.export_date}")
        texts.append("=" * 50)
        
        for i, node in enumerate(self.nodes, 1):
            texts.append(f"\n--- 对话片段 {i} ---\n")
            texts.append(node.to_text())
        
        if self.memory_events:
            texts.append("\n" + "=" * 50)
            texts.append("重要事件记录：")
            for event in self.memory_events:
                texts.append(event.to_text())
        
        return "\n".join(texts)


class DialogueParser:
    """对话解析器"""
    
    def parse_file(self, file_path: str) -> DialogueDocument:
        """解析JSON文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return self.parse(data)
    
    def parse(self, data: Dict[str, Any]) -> DialogueDocument:
        """解析JSON数据"""
        doc = DialogueDocument(
            export_version=data.get("exportVersion", "1.0"),
            export_date=data.get("exportDate", ""),
            character_name=data.get("character", {}).get("name", "未知角色")
        )
        
        # 解析对话节点
        dialogue_tree = data.get("dialogueTree", {})
        nodes = dialogue_tree.get("nodes", [])
        
        for node_data in nodes:
            node = DialogueNode(
                node_id=node_data.get("nodeId", ""),
                parent_node_id=node_data.get("parentNodeId"),
                user_input=node_data.get("userInput", ""),
                assistant_response=node_data.get("assistantResponse", ""),
                full_response=node_data.get("fullResponse", ""),
                parsed_content=node_data.get("parsedContent"),
                memory_snapshot=node_data.get("memorySnapshot")
            )
            doc.nodes.append(node)
            
            # 从记忆快照中提取事件
            if node.memory_snapshot:
                events = self._extract_memory_events(node.memory_snapshot)
                doc.memory_events.extend(events)
        
        return doc
    
    def _extract_memory_events(self, snapshot: Dict) -> List[MemoryEvent]:
        """从记忆快照中提取事件"""
        events = []
        sheets = snapshot.get("sheets", [])
        
        for sheet in sheets:
            if sheet.get("name") == "重要事件历史表格":
                rows = sheet.get("rows", [])
                for row in rows:
                    event = MemoryEvent(
                        character=row.get("角色", ""),
                        event_summary=row.get("事件简述", ""),
                        date=row.get("日期", ""),
                        location=row.get("地点", ""),
                        emotion=row.get("情绪", "")
                    )
                    events.append(event)
        
        return events


class TextChunker:
    """文本分块器"""
    
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_document(self, doc: DialogueDocument) -> List[Dict[str, Any]]:
        """将文档分块"""
        chunks = []
        
        # 按节点分块
        for i, node in enumerate(doc.nodes):
            text = node.to_text()
            if len(text) < 100:  # 跳过太短的节点
                continue
            
            chunks.append({
                "id": f"node_{i}",
                "text": text,
                "metadata": {
                    "type": "dialogue",
                    "node_id": node.node_id,
                    "character": doc.character_name,
                    "source": f"对话片段 {i+1}"
                }
            })
        
        # 添加事件历史作为独立块
        if doc.memory_events:
            event_texts = []
            for event in doc.memory_events:
                event_texts.append(event.to_text())
            
            events_text = "\n".join(event_texts)
            chunks.append({
                "id": "events_history",
                "text": f"重要事件历史记录：\n{events_text}",
                "metadata": {
                    "type": "memory_events",
                    "character": doc.character_name,
                    "source": "事件记录"
                }
            })
        
        return chunks
    
    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict[str, Any]]:
        """将长文本分块"""
        if len(text) <= self.chunk_size:
            return [{
                "id": "chunk_0",
                "text": text,
                "metadata": metadata or {}
            }]
        
        chunks = []
        start = 0
        chunk_idx = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # 尝试在句子边界处分块
            if end < len(text):
                # 找到最后一个句号、问号或感叹号
                last_punct = max(
                    text.rfind("。", start, end),
                    text.rfind("？", start, end),
                    text.rfind("！", start, end),
                    text.rfind(".", start, end)
                )
                if last_punct > start:
                    end = last_punct + 1
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "id": f"chunk_{chunk_idx}",
                    "text": chunk_text,
                    "metadata": {**(metadata or {}), "chunk_index": chunk_idx}
                })
                chunk_idx += 1
            
            start = end - self.overlap
            if start < 0:
                start = 0
            if start >= len(text):
                break
        
        return chunks
