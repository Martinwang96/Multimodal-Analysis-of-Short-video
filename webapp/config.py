"""Web 应用配置中心。

集中管理数据路径与运行参数，消除原脚本中的硬编码 Windows 路径。
所有路径基于项目根目录推导，便于迁移。
"""
from pathlib import Path

# 项目根目录（webapp 的上一级，即仓库根目录）
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据目录（原项目 CSV 所在位置 = 仓库根目录）
DATA_DIR = BASE_DIR

# 事件检测结果 CSV（02 阶段输出，核心数据契约）
EVENTS_CSV = DATA_DIR / "02_result_反方向的钟.csv"

# 原始对白 CSV
RAW_CSV = DATA_DIR / "原始数据集_反方向的钟_all.csv"

# 情感词典路径
LEXICON_PATH = Path(__file__).resolve().parent / "lexicon" / "sentiment_words.json"

# 情感正负分界阈值（与原项目 03_sentiment_analysis_v3.py 保持一致：正向概率 >= 0.5 为 positive）
SENTIMENT_THRESHOLD = 0.5

# 分页默认值
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

# CSV 上传限制
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {".csv"}

# 词频统计配置
TOP_WORDS_LIMIT = 20
WORDCLOUD_MAX = 120

# 中文停用词（短剧对白中高频无意义词）
STOPWORDS = set(list("的了是我你他她它们在也都有就都而要会着过这那一个么呢吧啊呀哦哎嗯呵哈啦哇呐诶与及以及或者还是被把将给跟和") + [
    "这个", "那个", "什么", "怎么", "为什么", "的话", "一个", "不是", "没有",
    "可以", "这么", "那么", "已经", "现在", "知道", "真的", "其实", "只是",
    "就是", "因为", "所以", "但是", "不过", "如果", "虽然", "然后", "这样",
    "那样", "自己", "他们", "我们", "你们", "这些", "那些", "对于", "关于",
    "觉得", "认为", "可能", "应该", "必须", "需要", "说明", "马上", "突然",
    "一下", "一些", "一直", "只有", "还有", "还是", "或者说", "不行", "不得",
])
