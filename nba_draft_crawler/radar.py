import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from math import pi


# ==========================================
# 1. 定义画图函数
# ==========================================
def create_radar_chart(player_name, player_stats, template_name, template_stats):
    # 定义维度
    categories = ['PTS', 'TRB', 'AST', 'eFG%']
    N = len(categories)

    # 计算角度
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]

    # 初始化图形
    plt.figure(figsize=(8, 8), dpi=150)  # 高清图，适合视频
    ax = plt.subplot(111, polar=True)

    # --- 设置坐标轴 ---
    plt.xticks(angles[:-1], categories, color='grey', size=12)
    ax.set_rlabel_position(0)
    plt.yticks([20, 40, 60, 80, 100], ["20%", "40%", "60%", "80%", "100%"], color="grey", size=10)
    plt.ylim(0, 120)

    # --- 数据处理：归一化 (为了画图好看，我们需要把数据转为相对值) ---
    # 简单的归一化逻辑：假设 PTS 满分是 35，TRB 满分 15，AST 满分 10，eFG 满分 0.7
    # 这只是为了视觉效果，不影响真实数据
    max_values = {'PTS': 35, 'TRB': 15, 'AST': 10, 'eFG%': 0.75}

    def normalize(stats):
        values = []
        values.append((stats['PTS_Per40'] / max_values['PTS']) * 100)
        values.append((stats['TRB_Per40'] / max_values['TRB']) * 100)
        values.append((stats['AST_Per40'] / max_values['AST']) * 100)
        values.append((stats['eFG%'] / max_values['eFG%']) * 100)
        return values

    # 获取数据并闭环
    values_p = normalize(player_stats)
    values_p += values_p[:1]

    values_t = normalize(template_stats)
    values_t += values_t[:1]

    # --- 画图: 新秀 ---
    ax.plot(angles, values_p, linewidth=2, linestyle='solid', label=f"{player_name} (2026)")
    ax.fill(angles, values_p, 'b', alpha=0.1)

    # --- 画图: 模板 ---
    ax.plot(angles, values_t, linewidth=2, linestyle='dashed', color='red', label=f"{template_name} (NBA Rookie Year)")
    ax.fill(angles, values_t, 'r', alpha=0.05)

    # --- 装饰 ---
    plt.title(f"Draft Comp: {player_name} vs {template_name}", size=20, color='black', y=1.1)
    plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))

    # 保存图片
    filename = f"{player_name}_vs_{template_name}.png".replace(" ", "_")
    plt.savefig(filename)
    print(f"图表已生成: {filename}")
    plt.close()


# ==========================================
# 2. 准备数据 (手动输入你的预测结果)
# ==========================================

# 你的预测结果里的 Zoom Diallo
zoom_diallo = {'PTS_Per40': 18.5, 'TRB_Per40': 6.2, 'AST_Per40': 5.8, 'eFG%': 0.48}  # 假设数据，你需要填入 CSV 里的真实数据
# 历史模板 Cade Cunningham
cade = {'PTS_Per40': 24.3, 'TRB_Per40': 7.5, 'AST_Per40': 4.2, 'eFG%': 0.510}

# 生成图表
create_radar_chart("Zoom Diallo", zoom_diallo, "Cade Cunningham", cade)