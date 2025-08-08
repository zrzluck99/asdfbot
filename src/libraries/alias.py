'''
pip install numpy unicodedata2 regex \
opencc-python-reimplemented python-Levenshtein \
torch transformers sentence-transformers \
faiss-cpu 
'''
# 请注意，这个代码片段是对 alias.py 的增强版本，它包含了更多的字符串匹配维度和动态权重调整。

import json
import re
import faiss
import Levenshtein
import unicodedata
import numpy as np
from opencc import OpenCC
from typing import List, Tuple, Dict
from sentence_transformers import SentenceTransformer
import time

class HybridStringMatcher:
    def __init__(self):
        # 多语言语义模型
        self.model = SentenceTransformer('./src/static/alias/paraphrase-multilingual-MiniLM-L12-v2')
        self.cc = OpenCC('t2s')  # 简繁转换
        
        # 索引系统
        self.index = None
        self.ids = []
        self.original_texts = []
        self.processed_texts = []
        
        # 字符匹配增强参数
        self.symbol_pattern = re.compile(r'[-_=+~・()（）]')
        self.weights = {
            'semantic': 0.5,
            'substring': 0.3,
            'levenshtein': 0.15,
            'char_jaccard': 0.05
        }

    def advanced_normalize(self, text: str) -> str:
        """增强型文本规范化"""
        # 统一Unicode表示
        text = unicodedata.normalize('NFKC', text)
        # 简繁转换
        text = self.cc.convert(text)
        # 移除特殊符号
        text = self.symbol_pattern.sub('', text)
        return text.lower().strip()

    def build_index(self, texts: Dict):
        flat_ids = []
        flat_texts = []
        for id_, aliases in texts.items():
            for alias in aliases:
                flat_ids.append(id_)
                flat_texts.append(alias)

        # 原始文本和处理后文本
        self.ids = flat_ids
        self.original_texts = flat_texts
        self.processed_texts = [self.advanced_normalize(t) for t in flat_texts]
        
        # 语义向量索引
        embeddings = self.model.encode(self.processed_texts,
                                     show_progress_bar=False,
                                     normalize_embeddings=True)
        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)

    def dynamic_weighting(self, query: str) -> dict:
        """根据查询长度动态调整权重"""
        query_len = len(query)
        base_weights = self.weights.copy()
        
        # 短查询强化字符匹配
        if query_len <= 4:
            base_weights['substring'] += 0.2
            base_weights['semantic'] -= 0.15
        # 中等长度平衡权重
        elif 5 <= query_len <= 8:
            base_weights['substring'] += 0.1
            base_weights['semantic'] -= 0.05
        # 长查询保持原权重
            
        # 标准化权重总和
        total = sum(base_weights.values())
        return {k: v/total for k, v in base_weights.items()}

    def calculate_similarities(self, query: str, target: str) -> dict:
        """计算多维度相似度"""
        return {
            'substring': self._substring_score(query, target),
            'levenshtein': self._levenshtein_sim(query, target),
            'char_jaccard': self._jaccard_sim(query, target),
        }

    def _substring_score(self, q: str, t: str) -> float:
        """增强子串匹配评分"""
        # 基础子串存在判断
        base_score = 1.0 if q in t else 0.0
        
        # 最长连续匹配奖励
        max_len = 0
        current = 0
        for char in q:
            if char in t:
                current += 1
                max_len = max(max_len, current)
            else:
                current = 0
        continuity_bonus = (max_len ** 1.5) / len(q)
        
        return base_score * 0.7 + continuity_bonus * 0.3

    def _levenshtein_sim(self, q: str, t: str) -> float:
        """归一化编辑距离相似度"""
        distance = Levenshtein.distance(q, t)
        max_len = max(len(q), len(t))
        return 1 - (distance / max_len)

    def _jaccard_sim(self, q: str, t: str) -> float:
        """字符集合相似度"""
        set_q = set(q)
        set_t = set(t)
        intersection = len(set_q & set_t)
        union = len(set_q | set_t)
        return intersection / union if union != 0 else 0

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """混合搜索主函数"""
        processed_query = self.advanced_normalize(query)
        dynamic_weights = self.dynamic_weighting(processed_query)
        
        # 获取语义相似候选
        query_vec = self.model.encode([processed_query])
        faiss.normalize_L2(query_vec)
        semantic_scores, indices = self.index.search(query_vec, len(self.original_texts))
        print("semantic_scores", semantic_scores[0])
        print("indices", indices[0])

        # 计算综合得分
        combined_scores = []
        for idx, score in zip(indices[0], semantic_scores[0]):
            orig_id = self.ids[idx]
            orig_text = self.original_texts[idx]
            proc_text = self.processed_texts[idx]
            
            # start = time.time()
            similarities = self.calculate_similarities(query, proc_text)
            similarities['semantic'] = score
            # end = time.time()

            # print(f"Time: {end - start}")
            total_score = sum(similarities[k] * dynamic_weights[k] for k in dynamic_weights)
            
            combined_scores.append((orig_id, orig_text, total_score))
        
        # 去重并排序
        seen = set()
        dedup_results = {}
        for id, text, score in sorted(combined_scores, key=lambda x: -x[2]):
            if id not in seen:
                seen.add(id)
                dedup_results[id] = (text, score)
            if len(seen) >= top_k:
                break
        
        return dedup_results
