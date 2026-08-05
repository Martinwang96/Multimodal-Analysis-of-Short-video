'''
Author: Martinwang96 -git
Date: 2025-05-03 10:09:24
Contact: martingwang01@163.com
LONG LIVE McDonald's
Copyright (c) 2025 by Martin Wang in Language of Sciences, Shanghai International Studies University, All Rights Reserved. 
'''
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from tqdm import tqdm
import os


# 1. 加载 Erlangshen-Roberta-110M-Sentiment 模型
model_name = 'IDEA-CCNL/Erlangshen-Roberta-110M-Sentiment'
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

# 如果有GPU则使用
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# 2. 读取数据
df = pd.read_csv('反方向的钟_hybrid_v5_events.csv')

# 3. 创建文件夹用于存储结果
result_dir = 'sentiment_results'
os.makedirs(result_dir, exist_ok=True)

# 4. 情感分析函数
def analyze_sentiment_erlangshen(text):
    if not text or len(text) < 2:
        return {"score": 0.5, "label": "neutral"}
    
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    with torch.no_grad():
        outputs = model(**inputs)
        scores = torch.softmax(outputs.logits, dim=1)
        neg_score = scores[0][0].item()
        pos_score = scores[0][1].item()
        label = "positive" if pos_score > neg_score else "negative"
        sentiment_score = pos_score
    
    return {"score": sentiment_score, "label": label}

# 5. 处理每个事件的所有文本，并计算事件级情感得分
def process_events(df):
    # 先为每个句子分析情感
    sentence_results = []
    print("分析各个句子的情感...")
    for _, row in tqdm(df.iterrows(), desc="句子情感分析进度", total=len(df)):
        erlangshen_result = analyze_sentiment_erlangshen(row['文本内容'])
        sentence_results.append({
            "事件ID": row['事件ID_Hybrid_V5'],
            "说话人": row['说话人'],
            "文本内容": row['文本内容'],
            "情感得分": erlangshen_result["score"],
            "情感标签": erlangshen_result["label"]
        })
    
    # 转换为DataFrame
    sentences_df = pd.DataFrame(sentence_results)
    
    # 计算每个事件的平均情感得分
    event_sentiments = sentences_df.groupby('事件ID')['情感得分'].mean().reset_index()
    event_sentiments.columns = ['事件ID', '事件情感得分']
    
    # 为每个事件确定情感标签
    event_sentiments['事件情感标签'] = event_sentiments['事件情感得分'].apply(
        lambda x: "positive" if x >= 0.5 else "negative"
    )
    
    # 合并相同事件ID下相同说话人的文本
    speaker_merged_results = []
    print("合并相同事件ID下相同说话人的文本...")
    for (event_id, speaker), group in df.groupby(['事件ID_Hybrid_V5', '说话人']):
        merged_text = " ".join(group['文本内容'].tolist())
        
        # 对合并后的文本进行情感分析
        erlangshen_result = analyze_sentiment_erlangshen(merged_text)
        
        speaker_merged_results.append({
            "事件ID": event_id,
            "说话人": speaker,
            "合并后的文本": merged_text,
            "说话人情感得分": erlangshen_result["score"],
            "说话人情感标签": erlangshen_result["label"]
        })
    
    speaker_merged_df = pd.DataFrame(speaker_merged_results)
    
    # 合并事件情感分数到原始数据中
    # 先将事件情感分数添加到说话人级别的数据
    final_speaker_results = pd.merge(speaker_merged_df, event_sentiments, on='事件ID', how='left')
    
    # 将事件情感分数添加到句子级别的数据
    final_sentence_results = pd.merge(sentences_df, event_sentiments, on='事件ID', how='left')
    
    return final_speaker_results, final_sentence_results, event_sentiments

# 6. 执行处理
speaker_results, sentence_results, event_sentiments = process_events(df)

# 7. 保存结果
print("保存结果...")
speaker_results.to_csv(os.path.join(result_dir, 'speaker_sentiment_results.csv'), index=False, encoding='utf-8-sig')
sentence_results.to_csv(os.path.join(result_dir, 'sentence_sentiment_results.csv'), index=False, encoding='utf-8-sig')
event_sentiments.to_csv(os.path.join(result_dir, 'event_sentiment_results.csv'), index=False, encoding='utf-8-sig')

# 8. 将事件级别情感得分添加到原始数据中，并保存
enhanced_df = pd.merge(df, event_sentiments, left_on='事件ID_Hybrid_V5', right_on='事件ID', how='left')
enhanced_df.to_csv(os.path.join(result_dir, 'enhanced_events_with_sentiment.csv'), index=False, encoding='utf-8-sig')
print("情感分析结果已保存到以下文件：")
print("1. speaker_sentiment_results.csv - 合并后的说话人级别情感")
print("2. sentence_sentiment_results.csv - 句子级别情感")
print("3. event_sentiment_results.csv - 事件级别情感得分")
print("4. enhanced_events_with_sentiment.csv - 原始数据增强版（带有事件情感得分）")
