'''
Author: Martinwang96 -git
Date: 2025-05-02 17:24:37
Contact: martingwang01@163.com
LONG LIVE McDonald's
Copyright (c) 2025 by Martin Wang in Language of Sciences, Shanghai International Studies University, All Rights Reserved. 

'''

import pandas as pd
# import spacy # SpaCy 未使用
from transformers import AutoTokenizer as AutoTokenizerGeneric, AutoModel # For BERTopic embeddings
from transformers import BertTokenizer as BertTokenizerForSim, BertForSequenceClassification # For Pairwise Similarity
import torch
from bertopic import BERTopic
import numpy as np
import os
import re
from tqdm import tqdm
# from scipy.spatial.distance import cosine # No longer needed for rule similarity

# --- 配置区域 ---
CSV_FILE_PATH = r'D:\桌面文件\研一下\机器学习\1-88\反方向的钟_all.csv'
OUTPUT_CSV_PATH = '反方向的钟_hybrid_v5_events.csv' # 输出文件名更新 (V5)

# Model for BERTopic Embeddings (General Purpose)
EMBEDDING_MODEL_NAME = 'IDEA-CCNL/Erlangshen-Ubert-330M-Chinese'

# Model for Pairwise Similarity Calculation (Fine-tuned)
SIMILARITY_MODEL_NAME = 'IDEA-CCNL/Erlangshen-Roberta-110M-Similarity'

BERTOPIC_LANGUAGE = "chinese"
BERTOPIC_MIN_TOPIC_SIZE = 6
BERTOPIC_NR_TOPICS = "auto"
MANUAL_EMBEDDING_BATCH_SIZE = 16 # For BERTopic embedding generation
SIMILARITY_BATCH_SIZE = 32       # For pairwise similarity calculation

# --- 预处理配置 ---
SENTENCE_ENDING_PUNCTUATION = set(['。', '！', '？', '…', '.', '!', '?'])

# --- 混合方法规则配置 (V5 - 使用直接相似度分数) ---
# Thresholds now apply to the probability score from the similarity model (0-1 range)
MERGE_SIMILARITY_THRESHOLD_STRONG = 0.90 # 覆盖Source Change的合并阈值 (需要根据新模型调整)
ADD_SIMILARITY_THRESHOLD_LOW = 0.30     # 不同人同源时，低相似度强制添加 (需要根据新模型调整)
MERGE_SIMILARITY_THRESHOLD_LOOSE = 0.80 # 不同人同源时，用于合并的宽松阈值 (需要根据新模型调整)

ADD_MARKER_SCORES = { 'but': 3.5, 'condition': 3.0, 'sequence_start': 1.5 }
ADD_MARKER_THRESHOLD = 0.8
FORCE_BOUNDARY_ON_SOURCE_CHANGE = True

# ==================================================
# === 中文复句关联词词典 (保持不变) ===
# ==================================================
class EventsExtraction:
    # ... (EventsExtraction 类保持不变) ...
    def __init__(self):
        self.but_wds = self.pattern_but()
        self.seq_wds = self.pattern_seq()
        self.condition_wds = self.pattern_condition()
        self.more_wds = self.pattern_more()
        self.all_patterns = {
            'but': self.but_wds, 'sequence': self.seq_wds,
            'condition': self.condition_wds, 'more': self.more_wds,
        }
        print(f"EventsExtraction 初始化完成。")

    # ... (pattern_* and check_utterance_start methods remain the same) ...
    '''转折事件关联词'''
    def pattern_but(self):
        wds = [[['与其'], ['不如'],'but'],
                [['虽然','尽管','虽'],['但也','但还','但却','但'],'but'],
                [['虽然','尽管','虽'],[ '但','但是也','但是还','但是却',],'but'],
                [['不是'],['而是'],'but'],
                [['即使','就算是'],['也','还'],'but'],
                [['即便'],['也','还'],'but'],
                [['虽然','即使'],['但是','可是','然而','仍然','还是','也', '但'],'but'],
                [['虽然','尽管','固然'],['也','还','却'],'but'],
                [['与其','宁可'],['决不','也不','也要'],'but'],
                [['与其','宁肯'],['决不','也要','也不'],'but'],
                [['与其','宁愿'],['也不','决不','也要'],'but'],
                [['虽然','尽管','固然'],['也','还','却'],'but'],
                [['虽'],['可是','倒','但','可','却','还是','但是'],'but'],
                [['虽然','纵然','即使'],['倒','还是','但是','但','可是','可','却'],'but'],
                [['虽说'],['还是','但','但是','可是','可','却'],'but'],
                [['与其'],['宁可','不如','宁肯','宁愿'],'but']]
        return wds

    '''顺承事件关联词'''
    def pattern_seq(self):
        wds =[
            [['又', '再', '才', '并'], ['进而'], 'sequence'],
            [['首先', '第一'], ['其次', '然后'], 'sequence'],
            [['首先', '先是'], ['再', '又', '还', '才'], 'sequence'],
            [['一方面'], ['另一方面', '又', '也', '还'], 'sequence']]
        return wds

    '''并列/递进/选择事件关联词'''
    def pattern_more(self):
        wds = [
                [['不但', '不仅'], ['并且'], 'more'],
                [['不单'], ['而且', '并且', '也', '还'], 'more'],
                [['不但'], ['而且', '并且', '也', '还'], 'more'],
                [['不光'], ['而且', '并且', '也', '还'], 'more'],
                [['虽然', '尽管'], ['不过'], 'more'],
                [['不仅'], ['还', '而且', '并且', '也'], 'more'],
                [['不只'], ['而且', '也', '并且', '还'], 'more'],
                [['不但', '不仅', '不光', '不只'], ['而且'], 'more'],
                [['尚且', '都', '也', '又', '更'], ['还', '又'], 'more'],
                [['无论', '不管', '不论', '或'], ['或'], 'choice'],
                [['或是'], ['或是'], 'choice'],
                [['或者', '无论', '不管', '不论'], ['或者'], 'choice'],
                [['不是'], ['也'], 'choice'],
                [['要么', '或者'], ['要么', '或者'], 'choice'],
        ]
        return wds

    '''条件事件关联词'''
    def pattern_condition(self):
        wds = [
                [['除非'], ['否则', '才', '不然', '要不'], 'condition'],
                [['除非'], ['否则的话'], 'condition'],
                [['既然'], ['又', '且', '也', '亦', '那么', '就', '便', '那'], 'condition'],
                [['假如','假若', '假使','如果','倘若', '要是'], ['那么', '就', '那', '则', '便','也', '还'], 'condition'],
                [['即使', '就是'], ['也', '还是'], 'condition'],
                [['如', '假设'], ['则', '那么', '就', '那'], 'condition'],
                [['万一'], ['那么', '就'], 'condition'],
                [['要是', '如果', '假如'], ['的话'], 'condition'],
                [['一旦'], ['就'], 'condition'],
                [['只要'], ['就', '便', '都', '总'], 'condition'],
                [['只有'], ['才', '还'], 'condition'],
        ]
        return wds

    def check_utterance_start(self, utterance_text):
        """检查话语开头是否匹配模式，返回最高优先级标签和得分"""
        text = utterance_text.strip(); best_label, best_score = None, 0.0
        if not text: return best_label, best_score
        # Prioritize 'but' and 'condition' types for adding boundaries
        for pattern_type in ['but', 'condition']:
            if pattern_type in self.all_patterns:
                score = ADD_MARKER_SCORES.get(pattern_type, 0)
                if score > best_score: # Check if this type has higher score potential
                    for pattern in self.all_patterns[pattern_type]:
                        # Check the second part of the pattern (the conjunction itself)
                        for word in pattern[1]:
                            if text.startswith(word):
                                # Found a match, return the highest score type found so far
                                return pattern_type, score # Return immediately
        # Check for sequence start markers ('firstly', etc.)
        pattern_type = 'sequence'
        label_for_score = 'sequence_start' # Use a specific label for scoring start markers
        if pattern_type in self.all_patterns:
            score = ADD_MARKER_SCORES.get(label_for_score, 0)
            if score > best_score: # Only check if score is higher than any but/condition found
                 for pattern in self.all_patterns[pattern_type]:
                     # Check the first part of the sequence pattern
                     for word in pattern[0]:
                          if text.startswith(word):
                              return label_for_score, score # Return immediately
        # No relevant marker found at the start
        return best_label, best_score


# ==================================================
# === 函数定义部分 ===
# ==================================================

# --- 数据加载与合并 (保持不变) ---
def load_dialogue_from_csv(csv_path):
    # ... (函数保持不变) ...
    """从 CSV 文件加载原始对话数据行"""
    if not os.path.exists(csv_path): print(f"错误：找不到 CSV 文件 '{csv_path}'"); return None
    try:
        df = pd.read_csv(csv_path)
        if not all(col in df.columns for col in ['说话人', '文本内容', 'source']): print(f"错误：CSV 文件 '{csv_path}' 必须包含 '说话人', '文本内容', 'source' 列"); return None
        raw_dialogue_rows = []
        skipped_count = 0
        for index, row in df.iterrows():
            speaker, utterance, source = row['说话人'], row['文本内容'], row['source']
            # Handle potential NaN/empty utterances more robustly
            if pd.isna(utterance) or not isinstance(utterance, str) or not utterance.strip():
                 # print(f"Skipping row {index + 2} due to empty or invalid utterance.")
                 skipped_count += 1
                 continue
            raw_dialogue_rows.append({
                "speaker": str(speaker).strip() if pd.notna(speaker) else "未知",
                "utterance": utterance.strip(),
                "source": source, # Keep original source, handle potential NaN later if needed
                "original_index": index
            })
        print(f"从 '{csv_path}' 加载了 {len(raw_dialogue_rows)} 条有效原始对话行 (跳过了 {skipped_count} 行)。")
        return raw_dialogue_rows
    except Exception as e: print(f"读取 CSV 文件 '{csv_path}' 时出错: {e}"); return None

def merge_dialogue_rows(raw_rows, ending_punctuation):
    # ... (函数保持不变) ...
    """合并同一说话人的连续行"""
    if not raw_rows: return []
    merged_dialogue = []
    current_merged_text = ""
    current_speaker = None
    current_source = None # Track source for the merged unit
    current_original_indices = []

    for i, row in enumerate(raw_rows):
        speaker, text, source, original_index = row["speaker"], row["utterance"], row["source"], row["original_index"]

        is_last_row = (i == len(raw_rows) - 1)
        next_speaker = raw_rows[i+1]["speaker"] if not is_last_row else None

        # Start of a new merged unit
        if not current_merged_text:
            current_merged_text = text
            current_speaker = speaker
            current_source = source # Use the source of the first row in the merged unit
            current_original_indices = [original_index]
        # Continue merging with the same speaker
        elif speaker == current_speaker:
            # Simple concatenation, consider adding space/comma if needed
            current_merged_text += text
            current_original_indices.append(original_index)
            # If source changes mid-merge, maybe prioritize the first source? Or handle differently?
            # Current logic uses the source of the *first* row of the merged unit.
        # Speaker changes, finalize the previous merged unit
        else:
            if current_merged_text:
                merged_dialogue.append({
                    "speaker": current_speaker,
                    "utterance": current_merged_text,
                    "source": current_source,
                    "original_indices": current_original_indices
                })
            # Start the new merged unit
            current_merged_text = text
            current_speaker = speaker
            current_source = source
            current_original_indices = [original_index]

        # Check conditions to finalize the *current* merged unit
        ends_with_punctuation = current_merged_text.endswith(tuple(ending_punctuation))
        speaker_changes_next = (not is_last_row and next_speaker != current_speaker)

        # Finalize if: ends with punctuation OR next speaker changes OR it's the very last row
        if ends_with_punctuation or speaker_changes_next or is_last_row:
            if current_merged_text:
                merged_dialogue.append({
                    "speaker": current_speaker,
                    "utterance": current_merged_text,
                    "source": current_source,
                    "original_indices": current_original_indices
                })
            # Reset for the next potential merged unit (or end)
            current_merged_text = ""
            current_speaker = None
            current_source = None
            current_original_indices = []

    print(f"预处理完成：将 {len(raw_rows)} 行合并为 {len(merged_dialogue)} 个对话单元。")
    return merged_dialogue


# --- 函数：为 BERTopic 生成嵌入向量 (使用通用模型) ---
def get_manual_embeddings(texts, model_name, batch_size=32):
    """手动加载 Transformer 模型(如Erlangshen-Ubert)并生成句子嵌入 (使用平均池化)"""
    print(f"开始使用 '{model_name}' 为BERTopic生成嵌入向量...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu"); print(f"  使用的设备: {device}")
    try:
        # Use AutoTokenizerGeneric for the general model
        tokenizer = AutoTokenizerGeneric.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name).to(device)
        model.eval()
    except Exception as e: print(f"  加载通用模型 '{model_name}' 或分词器时出错: {e}"); return None

    all_embeddings = []
    for i in tqdm(range(0, len(texts), batch_size), desc="  生成嵌入向量"):
        batch_texts = texts[i:i + batch_size]
        try:
            inputs = tokenizer(batch_texts, padding=True, truncation=True, return_tensors="pt", max_length=512).to(device)
            with torch.no_grad(): outputs = model(**inputs)
            last_hidden_states = outputs.last_hidden_state
            attention_mask = inputs['attention_mask']
            # Mean Pooling calculation
            mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_states.size()).float()
            sum_hidden_states = torch.sum(last_hidden_states * mask_expanded, 1)
            sum_mask = torch.clamp(mask_expanded.sum(1), min=1e-9) # Avoid division by zero
            mean_pooled_embeddings = sum_hidden_states / sum_mask
            all_embeddings.extend(mean_pooled_embeddings.cpu().numpy())
        except Exception as e:
            print(f"  处理批次 {i//batch_size} 时出错: {e}"); print(f"  跳过包含文本的批次: {batch_texts[:1]}...")
            embed_dim = model.config.hidden_size if hasattr(model.config, 'hidden_size') else 768
            all_embeddings.extend([np.zeros(embed_dim)] * len(batch_texts)) # Add zeros for failed batch

    print("BERTopic嵌入向量生成完毕。")
    # Final checks for consistency (same as before)
    if len(all_embeddings) != len(texts):
         print(f"  严重警告：生成的嵌入数量 ({len(all_embeddings)}) 与输入文本数量 ({len(texts)}) 不匹配！")
         embed_dim = model.config.hidden_size if hasattr(model.config, 'hidden_size') else 768
         diff = len(texts) - len(all_embeddings)
         if diff > 0: print(f"  填充 {diff} 个零向量..."); all_embeddings.extend([np.zeros(embed_dim)] * diff)
         elif diff < 0: print(f"  截断多余的 {abs(diff)} 个嵌入向量..."); all_embeddings = all_embeddings[:len(texts)]
    if any(e is None for e in all_embeddings):
        print("  警告：嵌入向量中包含 None 值，替换为零向量。")
        embed_dim = next((e.shape[0] for e in all_embeddings if e is not None), model.config.hidden_size if hasattr(model.config, 'hidden_size') else 768)
        all_embeddings = [e if e is not None else np.zeros(embed_dim) for e in all_embeddings]

    return np.array(all_embeddings)

# --- NEW 函数：计算相邻对话单元的直接相似度分数 (使用微调模型) ---
def calculate_pairwise_similarity_scores(utterances, model_name, batch_size=32):
    """
    使用专门的相似度模型 (如 Erlangshen-Roberta-Similarity)
    计算相邻句子对的相似度分数 (概率)。
    """
    print(f"\n开始使用 '{model_name}' 计算相邻单元的直接相似度分数...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu"); print(f"  使用的设备: {device}")
    if len(utterances) < 2: return np.array([])

    try:
        # Use BertTokenizerForSim for the similarity model
        tokenizer = BertTokenizerForSim.from_pretrained(model_name)
        model = BertForSequenceClassification.from_pretrained(model_name).to(device)
        model.eval()
    except Exception as e: print(f"  加载相似度模型 '{model_name}' 或分词器时出错: {e}"); return None

    similarity_scores = []
    num_pairs = len(utterances) - 1

    for i in tqdm(range(0, num_pairs, batch_size), desc="  计算相似度分数"):
        batch_pairs = []
        # Prepare pairs for the current batch
        for j in range(i, min(i + batch_size, num_pairs)):
            text_a = utterances[j]
            text_b = utterances[j+1]
            # Basic check for empty strings, though should be handled earlier
            if not text_a or not text_b:
                 batch_pairs.append(("", "")) # Handle empty strings gracefully if they appear
            else:
                 batch_pairs.append((text_a, text_b))

        if not batch_pairs: continue # Skip empty batches

        try:
            # Tokenize pairs: tokenizer.encode(text_a, text_b) format
            # Need to handle batch encoding correctly for pairs
            inputs = tokenizer(
                [pair[0] for pair in batch_pairs],
                [pair[1] for pair in batch_pairs],
                padding=True,
                truncation=True, # Truncate if combined length exceeds max_length
                return_tensors="pt",
                max_length=512 # Use appropriate max_length
            ).to(device)

            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits
                # Apply softmax to get probabilities
                probabilities = torch.nn.functional.softmax(logits, dim=-1)
                # *** IMPORTANT: Assume index 1 corresponds to "similar" ***
                # You might need to verify this based on the model's documentation or testing.
                # If index 0 is "similar", use probabilities[:, 0]
                sim_probs = probabilities[:, 1].cpu().numpy()
                similarity_scores.extend(sim_probs)

        except Exception as e:
            print(f"  处理相似度批次 {i//batch_size} 时出错: {e}")
            # Add default scores (e.g., 0.0) for the failed batch
            similarity_scores.extend([0.0] * len(batch_pairs))

    print(f"直接相似度分数计算完毕 (共 {len(similarity_scores)} 个)。")
    if len(similarity_scores) != num_pairs:
        print(f"  警告：计算出的相似度分数数量 ({len(similarity_scores)}) 与预期 ({num_pairs}) 不符！")
        # Pad or truncate if necessary, though batching logic should prevent this
        diff = num_pairs - len(similarity_scores)
        if diff > 0: similarity_scores.extend([0.0] * diff)
        elif diff < 0: similarity_scores = similarity_scores[:num_pairs]

    return np.array(similarity_scores)


# --- BERTopic 函数 (保持不变, 使用通用模型的嵌入) ---
def detect_boundaries_with_bertopic_manual_embeddings(dialogue_list, precomputed_embeddings, language, min_topic_size, nr_topics):
    # ... (函数保持不变, 使用 get_manual_embeddings 的输出) ...
    """使用 BERTopic 和预计算的嵌入进行主题建模，并检测初始边界"""
    if precomputed_embeddings is None or len(precomputed_embeddings) != len(dialogue_list):
        print("错误：用于BERTopic的预计算嵌入无效或数量与对话不匹配。")
        return None, None, None

    if len(dialogue_list) < 2:
        print("警告：对话单元数量少于2，无法进行BERTopic分析。")
        return None, None, None

    print(f"\n--- 开始使用 BERTopic (基于 '{EMBEDDING_MODEL_NAME}' 嵌入) 进行主题建模 ---")
    print(f"语言: {language}, MinTopicSize: {min_topic_size}, NrTopics: {nr_topics}, 嵌入维度: {precomputed_embeddings.shape[1]}, 输入单元数量: {len(dialogue_list)}")
    try:
        topic_model = BERTopic(embedding_model=None, # Crucial: Use precomputed embeddings
                               language=language,
                               min_topic_size=min_topic_size,
                               nr_topics=nr_topics,
                               calculate_probabilities=False,
                               verbose=True)
        # We need the utterances themselves for BERTopic's fit_transform context,
        # even though embeddings are precomputed.
        utterances = [item["utterance"] for item in dialogue_list]
        topics, _ = topic_model.fit_transform(utterances, embeddings=precomputed_embeddings) # Pass precomputed embeddings here

        print(f"BERTopic 分析完成。共找到 {len(np.unique(topics))} 个主题 (包括主题 -1)。")
        num_boundaries = len(topics) - 1
        boundaries = [False] * num_boundaries
        for i in range(num_boundaries):
            if topics[i] != topics[i+1]:
                 boundaries[i] = True
        print(f"根据主题变化，初步确定了 {sum(boundaries)} 个 BERTopic 边界点。")
        return topics, boundaries, topic_model
    except Exception as e:
        print(f"BERTopic 执行过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


# --- 混合方法边界细化逻辑 (V5 - 使用直接相似度分数) ---
def refine_boundaries_with_rules(
    dialogue_list,
    initial_boundaries,
    similarity_scores, # *** NOW expects the direct similarity scores (0-1) ***
    event_extractor,
    merge_similarity_threshold_strong=MERGE_SIMILARITY_THRESHOLD_STRONG,
    add_similarity_threshold_low=ADD_SIMILARITY_THRESHOLD_LOW,
    merge_similarity_threshold_loose=MERGE_SIMILARITY_THRESHOLD_LOOSE, # Added loose threshold
    add_marker_threshold=ADD_MARKER_THRESHOLD,
    force_boundary_on_source_change=FORCE_BOUNDARY_ON_SOURCE_CHANGE
    ):
    """根据优先级规则细化边界 (V5 - 使用直接相似度分数)"""
    if not dialogue_list or len(dialogue_list) < 2: return initial_boundaries

    refined_boundaries = list(initial_boundaries)
    num_potential_boundaries = len(dialogue_list) - 1
    print("\n--- 开始应用规则细化边界 (V5 - 使用直接相似度分数) ---")

    # Validate similarity_scores input
    if similarity_scores is None or len(similarity_scores) != num_potential_boundaries:
        print(f"警告：输入的相似度分数无效或数量 ({len(similarity_scores) if similarity_scores is not None else 'None'}) 与预期 ({num_potential_boundaries}) 不符！")
        print("基于相似度的规则将使用默认值 0.0。")
        similarities = [0.0] * num_potential_boundaries # Use default if scores are bad
    else:
        similarities = similarity_scores # Use the provided direct scores
        print(f"使用 {len(similarities)} 个由 '{SIMILARITY_MODEL_NAME}' 计算的直接相似度分数进行规则判断。")


    merge_count = 0; add_count = 0; force_merge_count = 0; force_add_count = 0

    for i in range(num_potential_boundaries):
        utt_i = dialogue_list[i]; utt_i_plus_1 = dialogue_list[i+1]
        is_same_speaker = (utt_i["speaker"] == utt_i_plus_1["speaker"])
        source_changed = (utt_i["source"] != utt_i_plus_1["source"])
        # Get the direct similarity score for this pair
        similarity = similarities[i] # Already a 0-1 score
        initial_decision = initial_boundaries[i]
        final_decision = initial_decision

        # --- 应用优先级规则 ---

        # 优先级 1: 同说话人 + 同Source -> 强制合并 (不分割)
        if is_same_speaker and not source_changed:
            if final_decision:
                final_decision = False
                force_merge_count += 1
            refined_boundaries[i] = final_decision
            continue

        # 优先级 2: Source 改变 -> 倾向分割，除非有强合并理由 (高相似度分数)
        elif source_changed:
            should_merge_override = False
            merge_override_reason = ""

            if similarity >= merge_similarity_threshold_strong:
                should_merge_override = True
                merge_override_reason = f"高相似度分数(>={merge_similarity_threshold_strong})"

            if should_merge_override:
                final_decision = False
                if initial_decision: merge_count += 1
            else:
                final_decision = True
                if not initial_decision: force_add_count += 1

            refined_boundaries[i] = final_decision
            continue

        # 优先级 3: 不同说话人 + 同Source -> 看标记词/低相似度添加，或中等相似度合并
        elif not is_same_speaker and not source_changed:
            final_decision = initial_decision
            reason = f"Spk不同Src相同, Init={initial_decision}"

            # 规则：考虑添加边界 (如果 BERTopic 没有分割)
            if not initial_decision:
                should_add = False; add_reason = ""
                marker_label, marker_score = event_extractor.check_utterance_start(utt_i_plus_1["utterance"])
                if marker_label and marker_score >= add_marker_threshold:
                    should_add = True; add_reason = f"强关联词({marker_label}|{marker_score:.1f})"
                elif similarity <= add_similarity_threshold_low: # Low direct similarity score
                    should_add = True; add_reason = f"低相似度分数(<={add_similarity_threshold_low})"

                if should_add:
                    final_decision = True
                    add_count += 1
                    reason += f", 规则添加:{add_reason}"

            # 规则：考虑移除边界 (如果 BERTopic 分割了)
            elif initial_decision:
                should_merge = False; merge_reason = ""
                # Use the loose similarity threshold
                if similarity >= merge_similarity_threshold_loose:
                     should_merge = True
                     merge_reason=f"较高相似度分数(>={merge_similarity_threshold_loose})"

                if should_merge:
                    final_decision = False
                    merge_count += 1
                    reason += f", 规则合并:{merge_reason}"

            refined_boundaries[i] = final_decision
            continue

        # 其他情况 (理论上不会到达)
        refined_boundaries[i] = initial_decision

    print(f"边界细化完成：强制合并 {force_merge_count}, 强制/维持分割 {force_add_count}, 规则合并 {merge_count}, 规则添加 {add_count}。")
    return refined_boundaries


# --- 后处理函数 (保持不变) ---
def post_process_remove_single_utterance_events(boundaries, num_units):
    # ... (函数保持不变) ...
    """移除导致单个合并单元成为独立事件的边界"""
    if num_units < 2: return boundaries
    final_boundaries = list(boundaries)
    removed_count = 0
    # Iterate up to the second to last potential boundary index
    for i in range(num_units - 2): # boundaries[i] and boundaries[i+1] must exist
        if final_boundaries[i] and final_boundaries[i+1]:
            # Found an isolated unit (unit i+1)
            final_boundaries[i] = False # Remove the first boundary
            removed_count += 1
            # Optional: print(f"Post-process: Removing boundary at index {i} to avoid isolating unit {i+1}")

    if removed_count > 0:
        print(f"后处理完成：移除了 {removed_count} 个导致单单元事件的边界。")
    return final_boundaries

# ==================================================
# === 主执行流程 ===
# ==================================================
if __name__ == "__main__":
    print("=== 开始执行对话事件边界检测 (混合方法 V5: 双模型 + 直接相似度) ===")

    # 1. 准备信息
    print(f"\n[步骤 1/8] 准备 NLP 模型信息...")
    print(f"  - 用于BERTopic嵌入的模型: {EMBEDDING_MODEL_NAME}")
    print(f"  - 用于规则相似度的模型: {SIMILARITY_MODEL_NAME}")
    event_marker_extractor = EventsExtraction()

    # 2. 加载原始对话数据
    print("\n[步骤 2/8] 加载原始对话数据...")
    raw_dialogue_data = load_dialogue_from_csv(CSV_FILE_PATH)
    if raw_dialogue_data is None or len(raw_dialogue_data) < 1: exit()

    # 3. 预处理：合并对话行
    print("\n[步骤 3/8] 预处理：合并连续对话行...")
    merged_dialogue_data = merge_dialogue_rows(raw_dialogue_data, SENTENCE_ENDING_PUNCTUATION)
    if not merged_dialogue_data or len(merged_dialogue_data) < 2:
        print("错误：预处理后对话单元不足 (<2)，无法进行边界检测。")
        # Handle single merged unit case (same as V4)
        if merged_dialogue_data and len(merged_dialogue_data) == 1:
            # ... (代码省略，与 V4 中处理单单元情况相同) ...
             print("只有一个合并单元，将其视为单个事件。")
             output_data = []
             event_id = 1
             topic_id = -1 # No BERTopic run
             is_new_event_start = True
             for i, raw_row in enumerate(raw_dialogue_data):
                  output_data.append({
                     '原始行号': raw_row["original_index"] + 2,
                     '说话人': raw_row['speaker'],
                     '文本内容': raw_row['utterance'],
                     'source': raw_row['source'],
                     'BERTopic主题ID_Erlangshen': topic_id,
                     '事件ID_Hybrid_V5': event_id, # V5
                     '是否为新事件开始_Hybrid_V5': is_new_event_start if i == 0 else False # V5
                  })
             output_df = pd.DataFrame(output_data)
             try:
                 output_df.to_csv(OUTPUT_CSV_PATH, index=False, encoding='utf-8-sig')
                 print(f"混合方法 V5 结果 (单事件) 已保存到: {OUTPUT_CSV_PATH}")
             except Exception as e: print(f"保存结果到 CSV 文件 '{OUTPUT_CSV_PATH}' 时出错: {e}")
        exit()
    num_merged_units = len(merged_dialogue_data)
    merged_utterances = [item["utterance"] for item in merged_dialogue_data] # Get text list


    # 4. 生成 BERTopic 嵌入向量 (使用通用模型)
    print(f"\n[步骤 4/8] 使用 '{EMBEDDING_MODEL_NAME}' 生成 BERTopic 嵌入向量...")
    bertopic_embeddings = get_manual_embeddings(merged_utterances, EMBEDDING_MODEL_NAME, batch_size=MANUAL_EMBEDDING_BATCH_SIZE)
    if bertopic_embeddings is None: exit()

    # 5. 使用 BERTopic 获取初始主题和边界
    print("\n[步骤 5/8] 使用 BERTopic 获取初始主题和边界...")
    assigned_topics, initial_boundary_flags, trained_topic_model = detect_boundaries_with_bertopic_manual_embeddings(
        merged_dialogue_data, bertopic_embeddings, BERTOPIC_LANGUAGE, BERTOPIC_MIN_TOPIC_SIZE, BERTOPIC_NR_TOPICS
    )
    if assigned_topics is None or initial_boundary_flags is None: exit()

    # 6. 计算相邻单元的直接相似度分数 (使用微调模型)
    print(f"\n[步骤 6/8] 使用 '{SIMILARITY_MODEL_NAME}' 计算直接相似度分数...")
    direct_similarity_scores = calculate_pairwise_similarity_scores(
        merged_utterances, SIMILARITY_MODEL_NAME, batch_size=SIMILARITY_BATCH_SIZE
    )
    if direct_similarity_scores is None:
        print("错误：未能计算直接相似度分数，规则细化将受影响。")
        # Provide default scores if calculation failed entirely
        direct_similarity_scores = np.zeros(num_merged_units - 1)


    # 7. 应用优先级规则细化边界 (V5 - 使用直接相似度分数)
    print("\n[步骤 7/8] 应用优先级规则细化边界 (V5)...")
    refined_boundary_flags = refine_boundaries_with_rules(
        merged_dialogue_data,
        initial_boundary_flags,
        direct_similarity_scores, # Pass the direct scores
        event_marker_extractor,
        # Pass thresholds relevant for direct scores
        merge_similarity_threshold_strong=MERGE_SIMILARITY_THRESHOLD_STRONG,
        add_similarity_threshold_low=ADD_SIMILARITY_THRESHOLD_LOW,
        merge_similarity_threshold_loose=MERGE_SIMILARITY_THRESHOLD_LOOSE,
        add_marker_threshold=ADD_MARKER_THRESHOLD,
        force_boundary_on_source_change=FORCE_BOUNDARY_ON_SOURCE_CHANGE
    )

    # 8. 后处理：移除单单元事件
    print("\n[步骤 8/8] 后处理：移除单单元事件...")
    final_boundary_flags = post_process_remove_single_utterance_events(
        refined_boundary_flags,
        num_merged_units
    )

    # 9. 映射最终结果回原始行并保存 CSV
    print("\n[步骤 9/8] 映射最终结果回原始行并保存到 CSV...") # Step number adjusted conceptually
    original_row_to_event = {}; original_row_to_topic = {}
    current_event_id = 1
    # Process first unit
    if merged_dialogue_data:
        first_merged_unit = merged_dialogue_data[0]
        topic_id = assigned_topics[0] if assigned_topics is not None else -99
        for original_idx in first_merged_unit["original_indices"]:
            original_row_to_event[original_idx] = current_event_id
            original_row_to_topic[original_idx] = topic_id
    # Process subsequent units based on final boundaries
    for i in range(len(final_boundary_flags)): # Iterate through boundary flags
        if final_boundary_flags[i]: current_event_id += 1 # Increment event ID if it's a boundary
        next_merged_unit_idx = i + 1
        if next_merged_unit_idx < num_merged_units:
            merged_unit = merged_dialogue_data[next_merged_unit_idx]
            topic_id = assigned_topics[next_merged_unit_idx] if assigned_topics is not None else -99
            for original_idx in merged_unit["original_indices"]:
                original_row_to_event[original_idx] = current_event_id # Assign current event ID
                original_row_to_topic[original_idx] = topic_id

    # Build output DataFrame
    output_data = []
    last_event_id = -1
    for i, raw_row in enumerate(raw_dialogue_data):
        original_idx = raw_row["original_index"]
        event_id = original_row_to_event.get(original_idx, -99)
        topic_id = original_row_to_topic.get(original_idx, -99)
        is_new_event_start = False
        if event_id != -99:
            if last_event_id == -1 or event_id != last_event_id:
                 is_new_event_start = True
            last_event_id = event_id

        output_data.append({
            '原始行号': original_idx + 2,
            '说话人': raw_row['speaker'],
            '文本内容': raw_row['utterance'],
            'source': raw_row['source'],
            'BERTopic主题ID_Erlangshen': topic_id, # Topic from general model
            '事件ID_Hybrid_V5': event_id,       # Event ID from V5 rules
            '是否为新事件开始_Hybrid_V5': is_new_event_start # V5 flag
        })

    output_df = pd.DataFrame(output_data)
    try:
        output_df.to_csv(OUTPUT_CSV_PATH, index=False, encoding='utf-8-sig')
        print(f"混合方法 V5 结果已保存到: {OUTPUT_CSV_PATH}")
    except Exception as e: print(f"保存结果到 CSV 文件 '{OUTPUT_CSV_PATH}' 时出错: {e}")

    # --- Optional: Print Topic Info & Preview ---
    if trained_topic_model:
        try:
            print(f"\n--- BERTopic 主题信息 (基于 '{EMBEDDING_MODEL_NAME}') ---")
            topic_info = trained_topic_model.get_topic_info()
            print(topic_info.head(20))
        except Exception as e: print(f"获取或打印主题信息时出错: {e}")

    print("\n--- 合并后的对话单元及 *最终* 边界预览 (前50个单元) ---")
    # ... (预览代码基本不变，只需更新列名/版本号 V5) ...
    print("=====================================")
    if merged_dialogue_data:
         first_unit = merged_dialogue_data[0]
         first_topic = assigned_topics[0] if assigned_topics is not None else 'N/A'
         first_event_id = original_row_to_event.get(first_unit['original_indices'][0], '?')
         print(f"--- 事件 {first_event_id} (Source: {first_unit['source']}, Topic: {first_topic}) ---")
         print(f"[{1:03d}|E:{first_event_id:>3}|T:{first_topic:>3}] {first_unit['speaker']}: {first_unit['utterance']}")
         last_topic_id_print = first_topic

         limit = min(50, len(merged_dialogue_data))
         for i in range(limit - 1): # Iterate up to the boundary before the 50th unit
             unit_idx = i + 1
             item = merged_dialogue_data[unit_idx]
             topic_id = assigned_topics[unit_idx] if assigned_topics is not None else 'N/A'
             unit_event_id = original_row_to_event.get(item['original_indices'][0], '?')

             # Check the boundary flag *before* this unit (index i)
             if i < len(final_boundary_flags) and final_boundary_flags[i]:
                 print(f"--------------------------- [最终边界点 {i} - 主题从 {last_topic_id_print} 变为 {topic_id}]")
                 next_source = item['source']
                 print(f"--- 事件 {unit_event_id} (Source: {next_source}, Topic: {topic_id}) ---")

             print(f"[{unit_idx+1:03d}|E:{unit_event_id:>3}|T:{topic_id:>3}] {item['speaker']}: {item['utterance']}")
             last_topic_id_print = topic_id

         if len(merged_dialogue_data) > 50: print("... (预览截断)")

    print("=====================================")
    print("=== 对话事件边界检测执行完毕 (混合方法 V5) ===")