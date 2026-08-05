# 短剧文本特征研究：以《反方向的钟》为例

本项目面向中文微短剧《反方向的钟》的多模态文本分析，构建了一条从音视频转写、事件划分、情感分析到结果可视化的处理流程。项目最初用于课程/小组展示，当前仓库版本更适合作为**研究复现**与**方法展示**型 GitHub 项目。

## 项目简介

微短剧具有“时长短、节奏快、反转强、情绪密度高”的传播特征，因此非常适合从文本、情感与叙事结构的角度进行计算分析。根据项目展示材料，本研究以《反方向的钟》为对象，先用 FunASR 完成中文转写与说话人分离，再使用 BERTopic + 相似度模型 + 规则系统做事件检测，随后进行事件级与说话人级情感分析，并结合可视化与 OpenFace 个案分析短剧叙事策略。 

## 项目目标

- 将短剧音视频转写为结构化对白数据
- 识别短剧中的事件边界，获得更适合后续分析的事件单元
- 计算句子级、说话人级、事件级情感得分
- 可视化不同角色与不同事件中的情感波动
- 为短剧叙事节奏、情绪转折和多模态个案分析提供数据支持

## 当前仓库包含的内容

当前上传的代码主要覆盖以下四个阶段：

1. **音视频转写与说话人分离前端**：`app_design_update.py`
2. **事件检测**：`02_events_process_v5.py`
3. **情感分析**：`03_sentiment_analysis_v3.py`
4. **结果可视化**：`04_visualization.py`

此外还包含：

- `download_model.py`：预下载 FunASR 所需模型
- `startup.bat`：Windows 下启动 GUI 的批处理文件
- `02_result_反方向的钟.csv`：一份中间/结果数据样例
- `看十遍《反方向的钟》能不能回到五一.pptx`：项目展示 PPT

> 说明：PPT 中还展示了 **OpenFace 面部表情分析** 这一部分，但目前上传的代码文件中没有对应的 OpenFace 处理脚本，因此本仓库现阶段的主流程仍以“转写—事件—情感—可视化”为主。

---

## 方法流程总览

```text
音视频文件
  ↓
FunASR 转写 + 说话人分离
  ↓
人工校对对白与说话人
  ↓
结构化 CSV
  ↓
BERTopic 初始事件边界检测
  ↓
相邻单元相似度计算
  ↓
规则细化事件边界
  ↓
事件级数据
  ↓
情感分析（句子 / 说话人 / 事件）
  ↓
可视化与个案分析
```

---

## 1. 音视频转写与说话人分离

### 脚本

- `app_design_update.py`
- `download_model.py`

### 功能

该部分基于 FunASR 构建了一个简单的 Tkinter 图形界面，用于：

- 批量选择音频或视频文件
- 调用 ASR、VAD、标点恢复、说话人分离模型
- 输出完整转写与逐句转写 CSV
- 按说话人切分音频/视频片段
- 生成按说话人聚合的音频文件

### 支持的输入格式

音频：`.mp3 .m4a .aac .ogg .wav .flac .wma .aif`  
视频：`.mp4 .avi .mov .mkv`

### 输出结果

程序会在所选保存目录下按日期和文件名创建子目录，主要产出包括：

- `完整转写.csv`
- `详细转写.csv`
- `spk*.txt`
- 按说话人切分后的音频/视频片段
- 每个说话人的合并音频文件

### 相关说明

- `download_model.py` 会预下载 FunASR 依赖的四个模型，便于首次运行前准备缓存。
- GUI 默认使用 CUDA，并通过 ffmpeg 先将输入转为 16k 单声道 wav 流，再送入 FunASR。
- 根据 PPT 说明，自动转写后的所有台词和说话人结果都经过了人工校对，再进入后续分析。

---

## 2. 事件检测（Event Segmentation）

### 脚本

- `02_events_process_v5.py`

### 输入

脚本读取一个包含以下字段的 CSV：

- `说话人`
- `文本内容`
- `source`

其中，`source` 可理解为集数或片段来源标记，用于帮助事件边界判断。

### 核心思路

该脚本使用“主题建模 + 相似度计算 + 规则系统”的混合方法做事件划分：

#### 2.1 对话单元预处理

- 删除空文本
- 合并同一说话人的连续发言
- 保留原始行号与来源信息，方便最后映射回原始 CSV

#### 2.2 初始事件边界

使用 `IDEA-CCNL/Erlangshen-Ubert-330M-Chinese` 生成对话单元嵌入，再交给 BERTopic 建模；当相邻单元主题发生变化时，先标记为潜在事件边界。

#### 2.3 相邻单元语义相似度

使用 `IDEA-CCNL/Erlangshen-Roberta-110M-Similarity` 计算相邻对话单元的直接相似度分数，用于后续边界修正。

#### 2.4 规则细化

脚本中实现了几类优先级规则：

- **同说话人 + 同 source**：强制合并，不分割
- **source 改变**：倾向于分割，除非相似度非常高
- **不同说话人 + 同 source**：结合相似度与中文关联词判断是否分割
- **后处理**：移除导致单个对话单元被孤立成事件的边界

另外，脚本内还维护了一个中文复句关联词词典，用于识别转折、条件、顺承等结构，帮助判断事件是否发生切换。

### 输出

输出文件默认为：

- `反方向的钟_hybrid_v5_events.csv`

主要字段包括：

- `原始行号`
- `说话人`
- `文本内容`
- `source`
- `BERTopic主题ID_Erlangshen`
- `事件ID_Hybrid_V5`
- `是否为新事件开始_Hybrid_V5`

这个文件也是后续情感分析的直接输入。

---

## 3. 情感分析

### 脚本

- `03_sentiment_analysis_v3.py`

### 输入

- `反方向的钟_hybrid_v5_events.csv`

### 模型

- `IDEA-CCNL/Erlangshen-Roberta-110M-Sentiment`

### 分析层级

该脚本不是只做一句一句的情感分类，而是同时输出三个层级：

#### 3.1 句子级情感

对 `文本内容` 逐行分析，输出：

- 情感得分
- 情感标签（positive / negative）

脚本将正向概率作为情感得分，并以 `0.5` 作为正负情绪分界线。

#### 3.2 事件级情感

对同一事件中的句子情感得分取算术平均，得到：

- `事件情感得分`
- `事件情感标签`

#### 3.3 说话人级情感

在同一事件内，将同一说话人的发言合并成一段文本后重新分析，从而得到更稳定的“角色在某事件中的态度”。

### 输出

程序会在 `sentiment_results/` 目录下生成：

- `speaker_sentiment_results.csv`
- `sentence_sentiment_results.csv`
- `event_sentiment_results.csv`
- `enhanced_events_with_sentiment.csv`

其中，`enhanced_events_with_sentiment.csv` 相当于在事件划分结果上追加了事件级情感信息，便于后续综合分析。

---

## 4. 可视化

### 脚本

- `04_visualization.py`

### 功能

该脚本读取情感分析结果并进行折线图绘制：

- 为每个说话人绘制随事件变化的情感得分图
- 绘制全局事件级情感得分图

### 输出

- `sentiment_plots/` 文件夹中的角色情感折线图
- 一个事件级情感得分图窗口

### 当前版本的特点

当前脚本更偏向“快速出图”的研究辅助脚本，适合本地探索式分析；如果后续要正式开源，建议进一步改造为：

- 使用命令行参数指定输入输出路径
- 去掉硬编码的 Windows 绝对路径
- 将 seaborn 绘图样式统一整理
- 增加图像自动命名和事件区间标记功能

---

## 5. PPT 中展示但当前仓库未完整公开的部分

根据展示材料，本项目后续还包括：

- 基于 OpenFace 的面部 Action Unit 分析
- 依据情感波动挑选片段做个案分析
- 将文本情感与视觉表情共同用于短剧叙事策略解释

PPT 中提到的分析逻辑包括：

- 通过 AU 组合识别表情类别，例如高兴可由 AU06 + AU12 激活判断
- 结合情感波动较大的片段做重点分析
- 关注短剧中的高频情绪切换、夸张表演与大特写镜头对叙事节奏的作用

如果后续补充 OpenFace 相关代码，这部分可以扩展为完整的多模态分析仓库。

---

## 推荐的仓库结构

考虑到当前文件既有脚本、结果，又有 PPT 和启动文件，比较适合整理为下面这种结构：

```text
.
├── README.md
├── requirements.txt
├── startup.bat
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
├── models/
│   └── download_model.py
├── scripts/
│   ├── 01_asr_gui.py
│   ├── 02_events_process_v5.py
│   ├── 03_sentiment_analysis_v3.py
│   └── 04_visualization.py
├── results/
│   ├── sentiment_results/
│   └── sentiment_plots/
├── docs/
│   └── project_presentation.pptx
└── assets/
    └── figures/
```

你也可以进一步把当前文件名规范化，例如：

- `app_design_update.py` → `01_asr_gui.py`
- `看十遍《反方向的钟》能不能回到五一.pptx` → `project_presentation.pptx`
- `02_result_反方向的钟.csv` → `sample_event_results.csv`

这样会更适合公开仓库阅读和复现。

---

## 环境建议

### 推荐 Python 版本

- Python 3.10 或 3.11

### 主要依赖

```bash
pandas
numpy
tqdm
torch
transformers
bertopic
matplotlib
seaborn
ffmpeg-python
pydub
funasr
modelscope
```

### 额外依赖

- 本机安装 `ffmpeg`
- 如需加速，建议配置 CUDA
- Windows 用户可直接使用批处理文件启动 GUI

---

## 基本使用流程

### 第一步：下载 FunASR 模型

```bash
python download_model.py
```

### 第二步：启动音视频转写 GUI

```bash
python app_design_update.py
```

或在 Windows 下直接运行：

```bash
startup.bat
```

### 第三步：人工校对转写结果

将 `详细转写.csv` 整理为后续事件检测所需格式，至少包含：

- `说话人`
- `文本内容`
- `source`

### 第四步：运行事件检测

```bash
python 02_events_process_v5.py
```

### 第五步：运行情感分析

```bash
python 03_sentiment_analysis_v3.py
```

### 第六步：生成可视化结果

```bash
python 04_visualization.py
```

---

## 当前版本的局限

1. **路径硬编码较多**  
   多个脚本中仍保留 Windows 本地绝对路径，迁移到其他机器前需要先修改。

2. **配置未参数化**  
   模型名、阈值、输入输出路径目前主要直接写在脚本顶部，适合实验，不够适合开源复现。

3. **缺少 requirements.txt / environment.yml**  
   目前仓库中没有完整依赖清单，建议补充。

4. **OpenFace 流程未纳入主仓库**  
   PPT 已经展示了该部分分析思路，但代码未随当前文件一并提供。

5. **数据清洗依赖人工校对**  
   这是研究上合理的做法，但在 README 中需要明确说明，以便他人理解自动与人工之间的边界。

---

## 适合作为 GitHub 项目的定位

我建议把这个项目定位为：

> **一个面向中文微短剧的多阶段分析流程示例项目**，展示如何从音视频出发，构建“转写—事件检测—情感分析—可视化”的研究型管线，并为多模态叙事分析提供可复用的方法框架。

这样的定位比单纯写成“课程作业代码”更适合 GitHub，也更利于你后续继续补充：

- OpenFace 表情分析
- 词频/词云/长度统计
- 跨剧比较
- 更规范的 CLI 与配置文件
- 论文或报告链接

---

## 致谢与参考方向

本项目在方法上综合使用了：

- FunASR：中文语音识别与说话人分离
- BERTopic：主题建模与事件边界初筛
- Fengshen / Erlangshen 系列模型：中文相似度与情感分析
- OpenFace：面部行为分析（见 PPT 展示）

如果你打算正式公开此仓库，建议在 README 末尾补充：

- 模型与工具的官方链接
- 原论文引用信息
- 你们小组成员分工
- 数据来源与使用说明

---

## 一句话总结

这是一个围绕《反方向的钟》构建的中文微短剧分析项目：从音视频出发，先把对白转成结构化数据，再识别事件边界、计算情感波动，并进一步服务于短剧叙事策略的多模态研究。
