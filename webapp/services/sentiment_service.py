"""词典情感分析服务。

基于内置中文情感词典对文本做正/负打分，无需 GPU/模型。
打分约定与原项目 03_sentiment_analysis_v3.py 一致：
- 正向概率作为情感得分（0-1）
- 0.5 为正负分界线
"""
import json
from collections import defaultdict

import jieba

from config import LEXICON_PATH, SENTIMENT_THRESHOLD


class SentimentService:
    """情感分析服务。Python 端用 jieba 分词匹配词典；JS 端用子串匹配。"""

    def __init__(self, lexicon_path=None):
        self.lexicon_path = lexicon_path or LEXICON_PATH
        self.positive = {}
        self.negative = {}
        self._load_lexicon()

    def _load_lexicon(self):
        with open(self.lexicon_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 去除词典中可能混入的空格键（书写误差），归一化
        self.positive = {k.strip(): float(v) for k, v in data.get("positive", {}).items() if k.strip()}
        self.negative = {k.strip(): float(v) for k, v in data.get("negative", {}).items() if k.strip()}

    def score_text(self, text):
        """单句打分。

        jieba 分词 → 词典匹配 → 加权统计
        Returns: {"score": float(0-1), "label": "positive"|"negative", "pos": float, "neg": float}
        """
        if not text or not isinstance(text, str) or len(text) < 1:
            return {"score": SENTIMENT_THRESHOLD, "label": "neutral", "pos": 0.0, "neg": 0.0}

        words = jieba.lcut(text)
        pos_sum = 0.0
        neg_sum = 0.0
        for w in words:
            w = w.strip()
            if not w:
                continue
            if w in self.positive:
                pos_sum += self.positive[w]
            if w in self.negative:
                neg_sum += self.negative[w]

        total = pos_sum + neg_sum
        if total <= 0:
            # 无情感词命中，视为中性
            score = SENTIMENT_THRESHOLD
        else:
            score = pos_sum / total

        label = "positive" if score >= SENTIMENT_THRESHOLD else "negative"
        return {"score": round(score, 4), "label": label, "pos": pos_sum, "neg": neg_sum}

    def score_sentences(self, texts):
        """批量句子级打分。"""
        return [self.score_text(t) for t in texts]

    def analyze_all(self, events_df):
        """对事件结果 DataFrame 做全量情感分析，返回三个层级结果。

        Returns:
            sentence_results: list[dict] 句子级
            event_results: list[dict] 事件级（同事件句子得分均值）
            speaker_results: list[dict] 说话人级（同事件内同说话人合并后打分）
        """
        sentence_results = []
        for _, row in events_df.iterrows():
            res = self.score_text(str(row["文本内容"]))
            sentence_results.append({
                "event_id": int(row["事件ID_Hybrid_V5"]),
                "speaker": str(row["说话人"]),
                "source": int(row["source"]),
                "text": str(row["文本内容"]),
                "score": res["score"],
                "label": res["label"],
            })

        # 事件级：同事件句子得分均值
        event_scores = defaultdict(list)
        for s in sentence_results:
            event_scores[s["event_id"]].append(s["score"])
        event_results = []
        for event_id, scores in sorted(event_scores.items()):
            avg = round(sum(scores) / len(scores), 4) if scores else SENTIMENT_THRESHOLD
            event_results.append({
                "event_id": event_id,
                "score": avg,
                "label": "positive" if avg >= SENTIMENT_THRESHOLD else "negative",
                "sentence_count": len(scores),
            })

        # 说话人级：同事件内同说话人合并文本后重新打分（与原项目逻辑一致）
        speaker_group = defaultdict(list)  # (event_id, speaker) -> [texts]
        for _, row in events_df.iterrows():
            key = (int(row["事件ID_Hybrid_V5"]), str(row["说话人"]))
            speaker_group[key].append(str(row["文本内容"]))

        speaker_results = []
        for (event_id, speaker), texts in sorted(speaker_group.items()):
            merged = " ".join(texts)
            res = self.score_text(merged)
            speaker_results.append({
                "event_id": event_id,
                "speaker": speaker,
                "score": res["score"],
                "label": res["label"],
                "line_count": len(texts),
            })

        return sentence_results, event_results, speaker_results


# 模块级单例
_service = None


def get_service():
    global _service
    if _service is None:
        _service = SentimentService()
    return _service
