"""事件聚合服务。

基于事件检测结果，统计每集事件数、事件大小分布、主题分布、事件时间线数据。
对应原项目 02_events_process_v5.py 的结果分析。
"""
from collections import Counter, defaultdict

from services.data_service import get_service as get_data_service


class EventService:
    """事件检测统计分析服务。"""

    def __init__(self):
        self.data_service = get_data_service()

    def get_events_per_source(self):
        """每集(source)的事件数分布。

        Returns:
            list[dict]: [{"source": int, "event_count": int, "line_count": int}, ...]
        """
        df = self.data_service.events_df
        result = []
        for source, group in df.groupby("source"):
            event_count = int(group["事件ID_Hybrid_V5"].nunique())
            line_count = int(len(group))
            result.append({
                "source": int(source),
                "event_count": event_count,
                "line_count": line_count,
            })
        result.sort(key=lambda x: x["source"])
        return result

    def get_event_size_distribution(self):
        """事件大小分布（每个事件包含的对白数）。"""
        df = self.data_service.events_df
        sizes = df.groupby("事件ID_Hybrid_V5").size().tolist()

        bins = [0, 2, 5, 10, 15, 20, 30, 50, 10000]
        labels = ["1-2", "3-5", "6-10", "11-15", "16-20", "21-30", "31-50", "50+"]
        hist = [0] * len(labels)
        for s in sizes:
            for i in range(len(bins) - 1):
                if bins[i] < s <= bins[i + 1]:
                    hist[i] += 1
                    break

        return {
            "distribution": [{"label": labels[i], "count": hist[i]} for i in range(len(labels))],
            "total_events": len(sizes),
            "avg_size": round(sum(sizes) / len(sizes), 1) if sizes else 0,
            "max_size": max(sizes) if sizes else 0,
            "min_size": min(sizes) if sizes else 0,
        }

    def get_topic_distribution(self):
        """BERTopic 主题分布。

        主题名根据该主题下全部对白的 jieba 高频词生成（Top 4，以·连接），
        使数字主题 ID 具备可读性；同时返回 keywords 列表供前端展示。
        """
        from collections import Counter

        from services.text_service import get_service as get_text_service

        df = self.data_service.events_df
        text_service = get_text_service()

        # 按主题聚合文本与计数
        topic_counts = Counter(df["BERTopic主题ID_Erlangshen"].tolist())
        topic_texts = {}
        for tid, text in zip(df["BERTopic主题ID_Erlangshen"], df["文本内容"].astype(str)):
            topic_texts.setdefault(int(tid), []).append(text)

        result = []
        for topic_id, count in sorted(topic_counts.items()):
            counter = Counter()
            for t in topic_texts.get(int(topic_id), []):
                counter.update(text_service._tokenize(t))
            top_words = [w for w, _ in counter.most_common(4)]
            if int(topic_id) == -1:
                name = "噪声"
            elif top_words:
                name = "·".join(top_words)
            else:
                name = f"主题 {topic_id}"
            result.append({
                "topic_id": int(topic_id),
                "count": int(count),
                "name": name,
                "keywords": top_words,
            })
        result.sort(key=lambda x: x["count"], reverse=True)
        return result

    def get_event_timeline(self):
        """事件时间线数据：按集排列的事件块。

        Returns:
            list[dict]: [{"event_id": int, "source": int, "line_count": int,
                          "speakers": [...], "start_row": int, "end_row": int}, ...]
        """
        df = self.data_service.events_df
        timeline = []
        for event_id, group in df.groupby("事件ID_Hybrid_V5"):
            sources = sorted(group["source"].unique().tolist())
            speakers = group["说话人"].unique().tolist()
            timeline.append({
                "event_id": int(event_id),
                "sources": [int(s) for s in sources],
                "primary_source": int(sources[0]),
                "line_count": int(len(group)),
                "speakers": speakers,
                "speaker_count": len(speakers),
                "start_row": int(group["原始行号"].min()),
                "end_row": int(group["原始行号"].max()),
            })
        timeline.sort(key=lambda x: x["event_id"])
        return timeline

    def get_source_event_matrix(self):
        """集 × 事件 矩阵数据，用于热力图。

        Returns:
            dict: {sources: [...], events: [...], data: [[source, event, count], ...]}
        """
        df = self.data_service.events_df
        matrix = defaultdict(int)
        for _, row in df.iterrows():
            matrix[(int(row["source"]), int(row["事件ID_Hybrid_V5"]))] += 1
        sources = sorted(df["source"].unique().tolist())
        # 仅取事件数较多的集用于可视化，避免矩阵过大
        data = [[int(s), int(e), int(c)] for (s, e), c in matrix.items()]
        return {
            "sources": [int(s) for s in sources],
            "data": data,
        }


# 模块级单例
_service = None


def get_service():
    global _service
    if _service is None:
        _service = EventService()
    return _service
