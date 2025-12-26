import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

# ==========================================
# 1. 准备“历史全明星”的大一数据 (训练集)
# ==========================================
# 这些数据是模型判断潜力的基准。
# 逻辑：如果你打得像大一的浓眉，那你就是状元。
# ==========================================
# 1. 修正后的历史数据 (Key名必须与 feature_cols 一致)
# ==========================================
historical_data = [
    # 注意：这里的 Key 必须是 PTS_Per40, TRB_Per40...
    {"Name": "Anthony Davis", "Pick": 1, "PTS_Per40": 20.5, "TRB_Per40": 15.3, "AST_Per40": 1.7, "eFG%": 0.628,
     "Type": "Big"},
    {"Name": "Zion Williamson", "Pick": 1, "PTS_Per40": 32.8, "TRB_Per40": 12.8, "AST_Per40": 3.0, "eFG%": 0.708,
     "Type": "Forward"},
    {"Name": "Paolo Banchero", "Pick": 1, "PTS_Per40": 23.6, "TRB_Per40": 10.5, "AST_Per40": 4.3, "eFG%": 0.525,
     "Type": "Forward"},
    {"Name": "Cade Cunningham", "Pick": 1, "PTS_Per40": 24.3, "TRB_Per40": 7.5, "AST_Per40": 4.2, "eFG%": 0.510,
     "Type": "Guard"},
    {"Name": "Evan Mobley", "Pick": 3, "PTS_Per40": 20.8, "TRB_Per40": 11.2, "AST_Per40": 3.1, "eFG%": 0.600,
     "Type": "Big"},
    {"Name": "Jayson Tatum", "Pick": 3, "PTS_Per40": 20.3, "TRB_Per40": 9.0, "AST_Per40": 2.6, "eFG%": 0.505,
     "Type": "Forward"},
    {"Name": "Trae Young", "Pick": 5, "PTS_Per40": 32.2, "TRB_Per40": 4.6, "AST_Per40": 10.3, "eFG%": 0.518,
     "Type": "Guard"},
    {"Name": "Bam Adebayo", "Pick": 14, "PTS_Per40": 18.2, "TRB_Per40": 10.9, "AST_Per40": 1.1, "eFG%": 0.600,
     "Type": "Big"},

    # --- 增加几个常见的模板，让结果更多样化 ---
    {"Name": "Tyrese Haliburton", "Pick": 12, "PTS_Per40": 17.5, "TRB_Per40": 6.8, "AST_Per40": 7.3, "eFG%": 0.610,
     "Type": "Guard"},
    {"Name": "Scottie Barnes", "Pick": 4, "PTS_Per40": 15.8, "TRB_Per40": 6.2, "AST_Per40": 6.4, "eFG%": 0.515,
     "Type": "Forward"},
]

df_history = pd.DataFrame(historical_data)

# ==========================================
# 2. 加载你的 2026 新秀数据 (测试集)
# ==========================================
try:
    df_prospects = pd.read_csv('ncaa_2026_prospects_fixed.csv')
    # 填充缺失值
    df_prospects = df_prospects.fillna(0)
except FileNotFoundError:
    print("错误：找不到 csv 文件，请先运行爬虫脚本！")
    exit()

# ==========================================
# 3. 特征工程与标准化
# ==========================================
# 我们选用的核心特征：得分、篮板、助攻、效率
feature_cols = ['PTS_Per40', 'TRB_Per40', 'AST_Per40', 'eFG%']

# 初始化标准化器 (非常重要！否则得分(30)会比效率(0.6)权重变得无限大)
scaler = StandardScaler()

# 拟合历史数据
X_history = scaler.fit_transform(df_history[feature_cols])

# 转换新秀数据 (注意：列名必须严格对应)
# 我们的爬虫结果里列名已经是 PTS_Per40 等，直接用
X_prospects = scaler.transform(df_prospects[feature_cols])

# ==========================================
# 4. 运行 KNN 算法 (寻找最佳模板)
# ==========================================
# n_neighbors=1 表示我们只找 1 个最像的模板
knn = NearestNeighbors(n_neighbors=1, algorithm='brute')
knn.fit(X_history)

# 计算距离和索引
distances, indices = knn.kneighbors(X_prospects)

# ==========================================
# 5. 生成预测报告
# ==========================================
results = []
print(f"正在分析 {len(df_prospects)} 名球员...\n")

for i in range(len(df_prospects)):
    # 获取新秀信息
    prospect_name = df_prospects.iloc[i]['Player']
    prospect_team = df_prospects.iloc[i]['Team']

    # 获取匹配到的历史球星索引
    match_idx = indices[i][0]
    match_distance = distances[i][0]  # 距离越小越像

    # 获取历史球星信息
    comp_player = df_history.iloc[match_idx]

    # 简单的评分逻辑：距离越近(similarity)，且模板顺位越高，评分越高
    # 这里我们只简单展示“最佳模板”
    results.append({
        "新秀": prospect_name,
        "学校": prospect_team,
        "最佳模板": comp_player['Name'],
        "模板当年顺位": comp_player['Pick'],
        "相似度距离": round(match_distance, 2)  # 越小越好
    })

# 转为 DataFrame 并排序
df_results = pd.DataFrame(results)

# 筛选：我们只关心那些像“前5顺位”球星的人
# 并且按“相似度”排序（距离越小，说明越像这个巨星）
top_prospects = df_results[df_results['模板当年顺位'] <= 5].sort_values(by='相似度距离')

# 展示前 10 名“具备巨星相”的球员
print("--- 2026 NBA 选秀预测模型 (基于大一数据相似度) ---")
print(top_prospects.head(10).to_string(index=False))

# 导出结果供视频制作
top_prospects.to_csv('2026_draft_prediction_report.csv', index=False)