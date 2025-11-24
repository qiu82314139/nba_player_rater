import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import cloudscraper
from io import StringIO
from math import pi

# --- 风格设置 ---
plt.rcParams['font.sans-serif'] = ['Arial', 'SimHei', 'DejaVu Sans'] 
plt.rcParams['axes.unicode_minus'] = False
plt.style.use('dark_background') # 全局暗黑模式

class RookieRankerPro:
    def __init__(self, year=2026):
        self.year = year
        self.url = f"https://www.basketball-reference.com/leagues/NBA_{year}_rookies.html"
        
        # === 核心升级：完全对应你的四维标准 ===
        self.weights = {
            'production': 0.35,  # 产出 (PTS, USG)
            'efficiency': 0.35,  # 效率 (TS%, AST/TO)
            'defense': 0.25,     # 防守 (STL, BLK, DREB)
            'winning': 0.05      # 赢球 (Game Score / PER 估算)
        }

    def get_mock_data(self):
        print("⚠️ 启用【模拟数据】模式...")
        # 模拟数据包含更多细节以支持高阶计算
        data = {
            'Player': ['Cooper Flagg', 'Ryan Kalkbrenner', 'VJ Edgecombe', 'Dylan Harper', 'Ace Bailey'],
            'PTS': [19.5, 14.2, 15.5, 16.8, 13.5],
            'TRB': [8.5, 9.1, 4.5, 4.2, 6.5],
            'AST': [4.5, 1.8, 3.5, 6.2, 2.5],
            'STL': [1.8, 0.5, 1.9, 1.5, 0.9],
            'BLK': [2.2, 2.8, 0.6, 0.4, 0.8],
            'TOV': [3.8, 1.1, 2.8, 3.5, 1.8],
            'FGA': [16.5, 8.5, 14.2, 15.1, 11.5],
            'FGM': [7.2, 6.1, 6.5, 6.8, 5.2], # 命中数
            'FTA': [6.5, 3.2, 4.1, 5.5, 3.2],
            'FTM': [4.8, 2.8, 3.2, 4.2, 2.5],
            'MP':  [33.5, 28.2, 30.5, 32.1, 29.5],
            'PF':  [3.2, 2.5, 2.8, 2.1, 2.5],
            'ORB': [2.1, 3.5, 0.8, 0.5, 1.5],
            'G':   [15, 15, 15, 15, 15]
        }
        df = pd.DataFrame(data)
        return df

    def fetch_data(self):
        print(f"🔍 正在获取 {self.year} 赛季数据 (四维评估版)...")
        
        try:
            scraper = cloudscraper.create_scraper()
            response = scraper.get(self.url)
            if response.status_code != 200:
                return self.get_mock_data()
            
            # 解析 BBR 表格
            # 尝试跳过第一行表头 (Per Game)
            try:
                dfs = pd.read_html(StringIO(response.text), attrs={'id': 'rookies'}, header=1)
            except:
                dfs = pd.read_html(StringIO(response.text), attrs={'id': 'rookies'}, header=0)

            if not dfs: return self.get_mock_data()
            
            df = dfs[0]
            df = df.loc[:, ~df.columns.duplicated()] # 去重列
            if 'Player' in df.columns: df = df[df['Player'] != 'Player']
            
            # 数值转换
            cols = ['PTS', 'TRB', 'AST', 'STL', 'BLK', 'TOV', 'FGA', 'FG', 'FTA', 'FT', 'MP', 'G', 'PF', 'ORB']
            for col in cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 如果没有 ORB (进攻篮板)，用 TRB 的 25% 估算
            if 'ORB' not in df.columns: df['ORB'] = df['TRB'] * 0.25
            if 'FG' not in df.columns: df['FG'] = df['PTS'] / 2 # 粗略估算防报错

            # 过滤
            df = df.dropna(subset=['PTS'])
            df = df[df['G'] >= 3]
            
            return df

        except Exception as e:
            print(f"❌ 数据获取异常: {e}")
            return self.get_mock_data()

    def calculate_scores(self, df):
        print("🧮 正在执行【四维评分标准】计算...")
        
        # 1. 准备基础高阶数据
        # TS% (真实命中率)
        df['TS_PCT'] = df['PTS'] / (2 * (df['FGA'].fillna(0) + 0.44 * df['FTA'].fillna(0)))
        
        # AST/TO (助攻失误比)
        df['AST_TO'] = df['AST'].fillna(0) / df['TOV'].replace(0, 1).fillna(1)
        
        # Est_USG (球权使用率估算) - 用于判断"持球核心"
        # 公式简化版: (FGA + 0.44*FTA + TOV)
        df['Possessions'] = df['FGA'] + 0.44 * df['FTA'] + df['TOV']
        # 这里我们用一个相对值，因为不知道球队总回合
        df['USG_Proxy'] = df['Possessions'] 

        # Game Score (赢球贡献值的硬核替代)
        # GmSc = PTS + 0.4 * FG - 0.7 * FGA - 0.4*(FTA - FT) + 0.7 * ORB + 0.3 * DRB + STL + 0.7 * AST + 0.7 * BLK - 0.4 * PF - TOV
        df['DRB'] = df['TRB'] - df['ORB']
        df['GmSc'] = (df['PTS'] + 0.4 * df['FG'] - 0.7 * df['FGA'] - 0.4 * (df['FTA'] - df['FT']) + 
                      0.7 * df['ORB'] + 0.3 * df['DRB'] + df['STL'] + 0.7 * df['AST'] + 0.7 * df['BLK'] - 
                      0.4 * df['PF'] - df['TOV'])

        # --- 归一化函数 (0-100分) ---
        def normalize(series, reverse=False):
            series = series.fillna(0)
            min_v, max_v = series.min(), series.max()
            if max_v == min_v: return 0
            if reverse: return (max_v - series) / (max_v - min_v) * 100
            return (series - min_v) / (max_v - min_v) * 100

        # === 维度一：产出 (Production) - 30% ===
        # 核心逻辑：得分 + 篮板 + 助攻 + 持球负荷(USG)
        # 法则1体现：引入 USG_Proxy 给持球大核加分
        df['Score_Prod'] = (normalize(df['PTS']) * 0.45 + 
                            normalize(df['USG_Proxy']) * 0.25 +  # 奖励高负荷
                            normalize(df['TRB']) * 0.15 + 
                            normalize(df['AST']) * 0.15)

        # === 维度二：效率 (Efficiency) - 30% ===
        # 核心逻辑：TS% + 助攻失误比 + 控制失误
        df['Score_Eff'] = (normalize(df['TS_PCT']) * 0.50 + 
                           normalize(df['AST_TO']) * 0.30 + 
                           normalize(df['TOV'], reverse=True) * 0.20)

        # === 维度三：防守 (Defense) - 25% ===
        # 核心逻辑：抢断 + 盖帽 + 防守篮板
        df['Score_Def'] = (normalize(df['STL']) * 0.40 + 
                           normalize(df['BLK']) * 0.40 + 
                           normalize(df['DRB']) * 0.20)

        # === 维度四：赢球 (Winning) - 15% ===
        # 核心逻辑：Game Score (单场影响力)
        df['Score_Win'] = normalize(df['GmSc'])

        # === 总分计算 ===
        df['Final_Score'] = (
            df['Score_Prod'] * self.weights['production'] +
            df['Score_Eff'] * self.weights['efficiency'] +
            df['Score_Def'] * self.weights['defense'] +
            df['Score_Win'] * self.weights['winning']
        )
        
        return df.sort_values(by='Final_Score', ascending=False).reset_index(drop=True)

    def generate_visuals(self, df, top_n=10):
        print("🎨 正在生成可视化套件...")
        
        # 1. 柱状排名图 (Bar Chart)
        top_df = df.head(top_n)
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # 配色：前三名用特别的金/银/铜色调，后面用渐变红
        palette = ['#FFD700', '#C0C0C0', '#CD7F32'] + sns.color_palette("flare_r", len(top_df)-3)
        
        bars = ax.barh(top_df['Player'], top_df['Final_Score'], color=palette)
        ax.invert_yaxis()
        
        ax.set_title(f"2025 ROOKIE LADDER: THE 4-DIMENSION MODEL", fontsize=22, fontweight='bold', color='white')
        
        for bar, row in zip(bars, top_df.itertuples()):
            width = bar.get_width()
            # 标签显示核心争议点：PTS vs TS%
            label = f" {width:.1f} | {row.PTS:.1f} pts | TS% {row.TS_PCT*100:.1f}% | GmSc {row.GmSc:.1f}"
            ax.text(width, bar.get_y() + bar.get_height()/2, label, ha='left', va='center', fontsize=10, color='white', fontweight='bold')
            
        ax.axis('off')
        plt.tight_layout()
        plt.savefig('rookie_rank_bar.png', dpi=300, facecolor='black')
        print("✅ 排名图已保存: rookie_rank_bar.png")

        # 2. 榜首雷达图 (Radar Chart)
        self.create_radar_chart(df.iloc[0], "rookie_radar_no1.png")
        # 如果有第二名，也生成一张对比
        if len(df) > 1:
            self.create_radar_chart(df.iloc[1], "rookie_radar_no2.png")

    def create_radar_chart(self, player_row, filename):
        # 准备数据
        categories = ['Production', 'Efficiency', 'Defense', 'Winning Impact']
        values = [
            player_row['Score_Prod'], 
            player_row['Score_Eff'], 
            player_row['Score_Def'], 
            player_row['Score_Win']
        ]
        
        # 雷达图闭环
        N = len(categories)
        angles = [n / float(N) * 2 * pi for n in range(N)]
        values += values[:1]
        angles += angles[:1]
        
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
        
        # 设置背景色和网格
        fig.patch.set_facecolor('black')
        ax.set_facecolor('#1a1a1a') # 深灰背景
        ax.spines['polar'].set_color('gray')
        
        # 绘制数据线
        ax.plot(angles, values, linewidth=2, linestyle='solid', color='#FFD700')
        ax.fill(angles, values, '#FFD700', alpha=0.4)
        
        # 设置标签
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, size=12, color='white', fontweight='bold')
        
        # 设置Y轴刻度 (不显示数字，只显示网格)
        ax.set_yticklabels([])
        ax.set_ylim(0, 100)
        
        # 标题
        plt.title(f"{player_row['Player']}\nTotal Score: {player_row['Final_Score']:.1f}", size=16, color='white', y=1.1)
        
        plt.tight_layout()
        plt.savefig(filename, dpi=300, facecolor='black')
        print(f"✅ 雷达图已保存: {filename}")

if __name__ == "__main__":
    # 2026 代表 2025-26 赛季
    ranker = RookieRankerPro(year=2026)
    df = ranker.fetch_data()
    ranked = ranker.calculate_scores(df)
    
    print("\n=== 🏆 新秀四维评分榜单 ===")
    # 打印详细评分卡
    print(ranked[['Player', 'Final_Score', 'Score_Prod', 'Score_Eff', 'Score_Def', 'Score_Win']].head(5))
    
    ranker.generate_visuals(ranked)