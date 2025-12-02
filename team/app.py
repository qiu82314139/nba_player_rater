import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import requests
from io import BytesIO
from PIL import Image
from nba_api.stats.endpoints import leaguedashteamstats

# ===========================
# --- 全局配置区域 ---
# ===========================
SEASON = '2025-26'  # 设置赛季

# 定义绘图风格
plt.style.use('seaborn-v0_8-whitegrid')
# 设置中文字体支持（可选，如果你的环境需要）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

# --- 核心配置字典：定义不同指标的绘图参数 ---
METRICS_CONFIG = {
    'NET_RATING': {
        'col_name': 'NET_RATING',
        'title': 'NBA 球队净效率 (Net Rating)',
        'ylabel': '百回合净胜分 (越高越好)',
        'invert_y': False,  # 数值越大越好，不需要反转Y轴（高分在上面）
        'ascending_sort': False  # 计算排名时，按降序排列（第一名是数值最大的）
    },
    'OFF_RATING': {
        'col_name': 'OFF_RATING',
        'title': 'NBA 球队进攻效率 (Offensive Rating)',
        'ylabel': '百回合得分 (越高越好)',
        'invert_y': False,  # 数值越大越好，不需要反转Y轴
        'ascending_sort': False  # 计算排名时，按降序排列
    },
    'DEF_RATING': {
        'col_name': 'DEF_RATING',
        'title': 'NBA 球队防守效率 (Defensive Rating)',
        'ylabel': '百回合失分 (越低越好)',
        'invert_y': True,  # 数值越小越好，需要反转Y轴（低分在上面）
        'ascending_sort': True  # 计算排名时，按升序排列（第一名是数值最小的）
    }
}

# Logo 映射修正 (处理少数 API 缩写与 ESPN 图源不一致的情况)
LOGO_MAPPING = {
    'UTA': 'uth', 'NOP': 'no', 'NYK': 'ny', 'GSW': 'gs', 'SAS': 'sa'
}


# ===========================
# 1. 数据获取与处理函数 (通用版)
# ===========================
def get_team_data(metric_config, season=SEASON):
    """
    根据传入的指标配置，获取数据并计算排名坐标
    """
    target_col = metric_config['col_name']
    sort_order_asc = metric_config['ascending_sort']

    print(f"正在抓取 {season} 赛季数据，目标指标: {target_col}...")

    # 获取联盟球队高阶数据
    # 注意：为了效率，我们一次性抓取所有数据，在内存中筛选
    try:
        stats = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            measure_type_nullable_default='Advanced',
            per_mode_detailed='PerGame',
            timeout=10  # 设置超时防止卡住
        )
        df = stats.get_data_frames()[0]
    except Exception as e:
        print(f"Error fetching data from NBA API: {e}")
        return pd.DataFrame()

    # 只选取需要的列
    df_filtered = df[['TEAM_ID', 'TEAM_ABBREVIATION', 'TEAM_NAME', target_col]].copy()

    # --- 核心逻辑：动态排序 ---
    # 根据配置决定是升序还是降序排列，以确定谁是第一名
    df_sorted = df_filtered.sort_values(by=target_col, ascending=sort_order_asc).reset_index(drop=True)

    # --- 创建 X 轴排名坐标 ---
    # 我们希望表现最好的球队在最右边 (X轴最大值)，表现最差的在最左边 (X轴最小值 1)
    # 无论按什么指标排序，排在 df_sorted 第一位的都是该指标下的 No.1
    # 所以 Rank 1 的 X 坐标为 30，Rank 30 的 X 坐标为 1
    df_sorted['X_Pos'] = len(df_sorted) - df_sorted.index

    return df_sorted


# ===========================
# 2. Logo 处理辅助函数 (保持不变)
# ===========================
def get_team_logo_imagebox(abbreviation, zoom=0.1):
    abbr_for_url = LOGO_MAPPING.get(abbreviation, abbreviation.lower())
    url = f"https://a.espncdn.com/i/teamlogos/nba/500/{abbr_for_url}.png"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        return OffsetImage(img, zoom=zoom)
    except Exception as e:
        print(f"Warning: 无法加载 {abbreviation} 的 Logo. 使用默认点代替。")
        return None


# ===========================
# 3. 主绘图函数 (通用版)
# ===========================
def create_logo_scatter_plot(df, metric_config, season=SEASON):
    """
    根据传入的数据和指标配置绘制图表
    """
    col_name = metric_config['col_name']
    title_text = metric_config['title']
    ylabel_text = metric_config['ylabel']
    do_invert_y = metric_config['invert_y']

    if df.empty:
        print("数据为空，跳过绘图。")
        return

    fig, ax = plt.subplots(figsize=(14, 9))

    print(f"开始绘制【{title_text}】，正在嵌入 Logo (预计耗时 20-30秒)...")

    # --- 核心循环：放置 Logo ---
    # 使用 iterrows 前先保存 Logo 对象以减少重复下载 (进阶优化，暂不实现以保持代码简单)
    # 这里简化处理，直接循环
    points_x = []
    points_y = []

    for index, row in df.iterrows():
        abbrev = row['TEAM_ABBREVIATION']
        x_pos = row['X_Pos']
        y_val = row[col_name]

        points_x.append(x_pos)
        points_y.append(y_val)

        # 获取图片对象，zoom 控制 Logo 大小 (0.09 比较适中)
        imagebox = get_team_logo_imagebox(abbrev, zoom=0.09)

        if imagebox:
            # frameon=False 去掉图片边框
            ab = AnnotationBbox(imagebox, (x_pos, y_val), frameon=False, box_alignment=(0.5, 0.5))
            ax.add_artist(ab)
        else:
            # 如果图片加载失败，画一个普通的点兜底
            ax.scatter(x_pos, y_val, c='gray', alpha=0.5)

    # --- 图表美化与坐标轴设置 ---

    # 动态设置 Y 轴范围，留一点边距
    y_min = df[col_name].min()
    y_max = df[col_name].max()
    # 对于净胜分这种可能跨越0的数据，边距计算要小心，这里简单处理
    buffer = (abs(y_max) + abs(y_min)) * 0.05 if y_max != y_min else 1.0
    ax.set_ylim(y_min - buffer, y_max + buffer)

    # 关键：根据配置决定是否反转 Y 轴
    if do_invert_y:
        ax.invert_yaxis()

    # 设置 X 轴范围
    ax.set_xlim(0, len(df) + 1)

    # 隐藏 X 轴刻度
    ax.set_xticks([])

    # 设置标题和标签
    plt.title(f"{title_text} [{season}]", fontsize=18, fontweight='bold', pad=20)
    ax.set_ylabel(ylabel_text, fontsize=13, labelpad=15)

    # 自定义网格线
    ax.grid(False)
    ax.grid(axis='y', color='gray', linestyle='--', linewidth=0.5, alpha=0.6)

    # 针对净胜分，加一条 0 的基准线
    if col_name == 'NET_RATING':
        ax.axhline(y=0, color='black', linewidth=1, linestyle='-', alpha=0.3)

    # 去掉边框
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # 添加来源说明
    plt.figtext(0.1, 0.03, 'Data Source: NBA API (stats.nba.com)', fontsize=9, color='gray')
    plt.figtext(0.9, 0.03, 'Visualization by Python Matplotlib', fontsize=9, color='gray', ha='right')

    plt.tight_layout()
    # 调整底部边距以防止文字被遮挡
    plt.subplots_adjust(bottom=0.1)
    print(f"【{title_text}】绘制完成！请查看弹出的窗口。")
    plt.show()


# ===========================
# 4. 主执行逻辑
# ===========================
if __name__ == "__main__":
    # 定义要生成的图表列表
    metrics_to_plot = ['NET_RATING', 'OFF_RATING', 'DEF_RATING']

    # 循环生成每一张图
    for metric_key in metrics_to_plot:
        print(f"\n{'=' * 30}\n准备生成: {metric_key}\n{'=' * 30}")

        # 1. 获取当前指标的配置
        config = METRICS_CONFIG[metric_key]

        # 2. 获取并处理数据
        df_metric = get_team_data(config, SEASON)

        # 3. 绘图
        create_logo_scatter_plot(df_metric, config, SEASON)