"""数据加载与查询服务。

懒加载 CSV 为 DataFrame，提供按事件/集/说话人筛选与分页查询。
不修改原始 CSV，仅读取。
"""
import pandas as pd

from config import EVENTS_CSV, RAW_CSV, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


class DataService:
    """数据服务单例。读取事件检测结果 CSV 与原始对白 CSV。"""

    def __init__(self, events_csv=None, raw_csv=None):
        self.events_csv = events_csv or EVENTS_CSV
        self.raw_csv = raw_csv or RAW_CSV
        self._events_df = None
        self._raw_df = None

    # ---------- 数据加载 ----------
    def _load_events(self):
        """加载事件检测结果 CSV。"""
        if not self.events_csv.exists():
            raise FileNotFoundError(f"事件结果 CSV 不存在: {self.events_csv}")
        df = pd.read_csv(self.events_csv)
        # 标准化列名访问（CSV 列名可能含中文，保留原名）
        # 事件 ID 强制为 int
        if "事件ID_Hybrid_V5" in df.columns:
            df["事件ID_Hybrid_V5"] = pd.to_numeric(df["事件ID_Hybrid_V5"], errors="coerce").fillna(1).astype(int)
        if "source" in df.columns:
            df["source"] = pd.to_numeric(df["source"], errors="coerce").fillna(1).astype(int)
        if "BERTopic主题ID_Erlangshen" in df.columns:
            df["BERTopic主题ID_Erlangshen"] = pd.to_numeric(
                df["BERTopic主题ID_Erlangshen"], errors="coerce").fillna(-1).astype(int)
        # 文本内容空值填充
        if "文本内容" in df.columns:
            df["文本内容"] = df["文本内容"].fillna("").astype(str)
        if "说话人" in df.columns:
            df["说话人"] = df["说话人"].fillna("未知").astype(str).str.strip()
        # 事件开始标志标准化（CSV 中为 TRUE/FALSE 字符串，避免 bool("FALSE") 误判）
        if "是否为新事件开始_Hybrid_V5" in df.columns:
            df["是否为新事件开始_Hybrid_V5"] = (
                df["是否为新事件开始_Hybrid_V5"].astype(str).str.upper().isin(["TRUE", "1", "YES"])
            )
        self._events_df = df
        return df

    def _load_raw(self):
        """加载原始对白 CSV（若存在）。"""
        if not self.raw_csv.exists():
            return None
        df = pd.read_csv(self.raw_csv)
        if "文本内容" in df.columns:
            df["文本内容"] = df["文本内容"].fillna("").astype(str)
        if "说话人" in df.columns:
            df["说话人"] = df["说话人"].fillna("未知").astype(str).str.strip()
        if "source" in df.columns:
            df["source"] = pd.to_numeric(df["source"], errors="coerce").fillna(1).astype(int)
        self._raw_df = df
        return df

    @property
    def events_df(self):
        if self._events_df is None:
            self._load_events()
        return self._events_df

    @property
    def raw_df(self):
        if self._raw_df is None:
            self._load_raw()
        return self._raw_df

    # ---------- 概览指标 ----------
    def get_overview(self):
        """返回项目关键指标。"""
        df = self.events_df
        total_lines = len(df)
        event_ids = df["事件ID_Hybrid_V5"].unique()
        total_events = int(len(event_ids))
        sources = df["source"].unique()
        total_sources = int(len(sources))
        speakers = df["说话人"].unique()
        total_speakers = int(len(speakers))
        return {
            "total_lines": total_lines,
            "total_events": total_events,
            "total_sources": total_sources,
            "total_speakers": total_speakers,
            "min_event_id": int(event_ids.min()) if len(event_ids) else 0,
            "max_event_id": int(event_ids.max()) if len(event_ids) else 0,
            "min_source": int(sources.min()) if len(sources) else 0,
            "max_source": int(sources.max()) if len(sources) else 0,
        }

    # ---------- 角色统计 ----------
    def get_speakers(self):
        """返回各角色台词数量、总字数、平均字数。"""
        df = self.events_df
        grouped = df.groupby("说话人")
        result = []
        for speaker, group in grouped:
            texts = group["文本内容"].astype(str)
            count = int(len(group))
            total_len = int(texts.str.len().sum())
            avg_len = round(total_len / count, 1) if count else 0
            result.append({
                "speaker": speaker,
                "line_count": count,
                "total_chars": total_len,
                "avg_chars": avg_len,
            })
        result.sort(key=lambda x: x["line_count"], reverse=True)
        return result

    # ---------- 事件汇总 ----------
    def get_events_summary(self):
        """返回各事件的汇总：事件ID、所属集、对白数、主题ID、起止行号。"""
        df = self.events_df
        rows = []
        for event_id, group in df.groupby("事件ID_Hybrid_V5"):
            sources = group["source"].unique().tolist()
            topics = group["BERTopic主题ID_Erlangshen"].unique().tolist()
            speakers = group["说话人"].unique().tolist()
            rows.append({
                "event_id": int(event_id),
                "sources": sources,
                "line_count": int(len(group)),
                "topics": [int(t) for t in topics],
                "speakers": speakers,
                "start_row": int(group["原始行号"].min()),
                "end_row": int(group["原始行号"].max()),
                "preview": " ".join(group["文本内容"].astype(str).tolist()[:3]),
            })
        rows.sort(key=lambda x: x["event_id"])
        return rows

    # ---------- 对话查询（筛选+分页）----------
    def query_dialogues(self, event_id=None, source=None, speaker=None,
                        keyword=None, page=1, size=None):
        """筛选并分页查询对话行。

        Args:
            event_id: 事件 ID 筛选
            source: 集(source)筛选
            speaker: 说话人筛选
            keyword: 文本关键词筛选
            page: 页码（从1开始）
            size: 每页条数
        Returns:
            dict: {items, total, page, pages, size}
        """
        df = self.events_df
        mask = pd.Series([True] * len(df), index=df.index)

        if event_id is not None:
            mask &= df["事件ID_Hybrid_V5"] == int(event_id)
        if source is not None:
            mask &= df["source"] == int(source)
        if speaker:
            mask &= df["说话人"] == speaker
        if keyword:
            mask &= df["文本内容"].astype(str).str.contains(keyword, na=False)

        filtered = df[mask]
        total = int(len(filtered))
        size = min(size or DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
        size = max(size, 1)
        pages = (total + size - 1) // size if total > 0 else 0
        page = max(min(page, pages if pages > 0 else 1), 1)

        start = (page - 1) * size
        end = start + size
        page_df = filtered.iloc[start:end]

        items = []
        for _, row in page_df.iterrows():
            items.append({
                "row_no": int(row["原始行号"]) if "原始行号" in row else 0,
                "speaker": str(row["说话人"]),
                "text": str(row["文本内容"]),
                "source": int(row["source"]),
                "event_id": int(row["事件ID_Hybrid_V5"]),
                "topic_id": int(row["BERTopic主题ID_Erlangshen"]),
                "is_new_event": bool(row["是否为新事件开始_Hybrid_V5"]) if "是否为新事件开始_Hybrid_V5" in row else False,
            })

        # 涉及的事件数与角色数
        involved_events = int(filtered["事件ID_Hybrid_V5"].nunique()) if total > 0 else 0
        involved_speakers = int(filtered["说话人"].nunique()) if total > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "pages": pages,
            "size": size,
            "involved_events": involved_events,
            "involved_speakers": involved_speakers,
        }

    # ---------- 选项列表 ----------
    def get_source_list(self):
        """返回所有集(source)列表。"""
        df = self.events_df
        return sorted([int(s) for s in df["source"].unique()])

    def get_speaker_list(self):
        """返回所有说话人列表。"""
        df = self.events_df
        return sorted(df["说话人"].unique().tolist())


# 模块级单例
_service = None


def get_service():
    global _service
    if _service is None:
        _service = DataService()
    return _service
