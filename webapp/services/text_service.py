"""文本统计服务。

jieba 分词 + 停用词过滤 → 词频统计；角色台词数量/长度统计；字数/词数分布。
对应原项目 01_文本分析_basis.ipynb 的分析内容。
"""
from collections import Counter

import jieba

from config import STOPWORDS, TOP_WORDS_LIMIT, WORDCLOUD_MAX
from services.data_service import get_service as get_data_service


class TextService:
    """文本统计分析服务。"""

    def __init__(self):
        self.data_service = get_data_service()

    def _tokenize(self, text):
        """分词并过滤停用词与单字标点。"""
        words = jieba.lcut(str(text))
        result = []
        for w in words:
            w = w.strip()
            if not w:
                continue
            if w in STOPWORDS:
                continue
            if len(w) < 2 and w not in ("爱", "恨", "哭", "笑", "死", "错", "对", "好", "坏"):
                # 保留少量有情感意义的单字，其余单字过滤
                continue
            result.append(w)
        return result

    def get_word_frequency(self, limit=None):
        """全剧词频统计。

        Returns:
            list[dict]: [{"word": str, "count": int}, ...] 按频次降序
        """
        limit = limit or TOP_WORDS_LIMIT
        df = self.data_service.events_df
        counter = Counter()
        for text in df["文本内容"].astype(str):
            counter.update(self._tokenize(text))

        words = counter.most_common(max(limit, WORDCLOUD_MAX))
        top = words[:limit]
        return {
            "top_words": [{"word": w, "count": c} for w, c in top],
            "wordcloud_words": [{"name": w, "value": c} for w, c in words[:WORDCLOUD_MAX]],
        }

    def get_speaker_word_frequency(self, speaker, limit=30):
        """指定角色的词频统计。"""
        df = self.data_service.events_df
        speaker_df = df[df["说话人"] == speaker]
        counter = Counter()
        for text in speaker_df["文本内容"].astype(str):
            counter.update(self._tokenize(text))
        words = counter.most_common(limit)
        return [{"name": w, "value": c} for w, c in words]

    def get_text_distribution(self):
        """字数分布与词数分布。

        Returns:
            dict: 字数直方图数据 + 词数统计
        """
        df = self.data_service.events_df
        texts = df["文本内容"].astype(str)
        char_lengths = texts.str.len().tolist()
        word_lengths = [len(self._tokenize(t)) for t in texts]

        # 字数直方图分箱
        bins = [0, 5, 10, 15, 20, 30, 50, 80, 120, 200, 10000]
        labels = ["1-5", "6-10", "11-15", "16-20", "21-30", "31-50", "51-80", "81-120", "121-200", "200+"]
        hist = [0] * len(labels)
        for cl in char_lengths:
            for i in range(len(bins) - 1):
                if bins[i] < cl <= bins[i + 1]:
                    hist[i] += 1
                    break

        return {
            "char_distribution": [{"label": labels[i], "count": hist[i]} for i in range(len(labels))],
            "char_stats": {
                "min": int(min(char_lengths)) if char_lengths else 0,
                "max": int(max(char_lengths)) if char_lengths else 0,
                "avg": round(sum(char_lengths) / len(char_lengths), 1) if char_lengths else 0,
            },
            "word_stats": {
                "min": int(min(word_lengths)) if word_lengths else 0,
                "max": int(max(word_lengths)) if word_lengths else 0,
                "avg": round(sum(word_lengths) / len(word_lengths), 1) if word_lengths else 0,
            },
        }


# 模块级单例
_service = None


def get_service():
    global _service
    if _service is None:
        _service = TextService()
    return _service
