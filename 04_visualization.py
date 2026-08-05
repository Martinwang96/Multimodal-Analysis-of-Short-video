'''
Author: Martinwang96 -git
Date: 2025-05-03 11:44:04
Contact: martingwang01@163.com
LONG LIVE McDonald's
Copyright (c) 2025 by Martin Wang in Language of Sciences, Shanghai International Studies University, All Rights Reserved. 
'''
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置中文字体
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 文件路径
input_file_path = r'D:\桌面文件\研一下\机器学习\sentiment_results\sentence_sentiment_results.csv'
event_file_path = r'D:\桌面文件\研一下\机器学习\sentiment_results\event_sentiment_results.csv'

# 读取数据
df = pd.read_csv(input_file_path)

# 创建一个新的图表文件夹，用于保存每个说话人的情感得分图
output_dir = 'sentiment_plots'
os.makedirs(output_dir, exist_ok=True)

# 为每个说话人单独绘制情感得分图
speakers = df['说话人'].unique()

for speaker in speakers:
    # 筛选该说话人的数据
    speaker_data = df[df['说话人'] == speaker]
    
    # 创建绘图
    plt.figure(figsize=(10, 6))
    sns.lineplot(data=speaker_data, x='事件ID', y='情感得分')
    
    # 设置标题和标签
    plt.title(f'{speaker} 情感得分分布')
    plt.xlabel('事件ID')
    plt.ylabel('情感得分')
    plt.xticks(rotation=90)
    
    # 保存每个图表为文件
    plt.tight_layout()
    plt.savefig(f'{output_dir}/{speaker}_sentiment_plot.png', dpi=300)
    plt.close()

print(f"所有图表已保存到 {output_dir} 文件夹。")

# 读取事件级别的情感得分数据
df_event = pd.read_csv(event_file_path)
df_event_sentiment = df_event[['事件ID', '事件情感得分']]

# 绘制事件级别情感得分图
plt.figure(figsize=(10, 6))
sns.lineplot(data=df_event_sentiment, x='事件ID', y='事件情感得分')
plt.title('事件级别情感得分分布')
plt.xlabel('事件ID')
plt.ylabel('事件情感得分')
plt.xticks(rotation=90)
plt.tight_layout()
plt.show()
