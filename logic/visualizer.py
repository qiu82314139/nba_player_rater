from typing import Dict
import matplotlib.pyplot as plt
import numpy as np

def draw_radar_chart(scores: Dict[str, int], color_hex: str):
    labels = ["Scoring", "Playmaking", "Defense", "Rebounding", "Isolation", "Clutch"]
    values = [scores.get(l, 60) for l in labels]
    values += values[:1]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]
    fig = plt.figure(figsize=(6, 6))
    ax = plt.subplot(111, polar=True)
    fig.patch.set_alpha(0.0)
    ax.set_facecolor('#1e1e1e')
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_rlabel_position(0)
    ax.set_ylim(50, 100)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, color='white')
    ax.set_yticks([60, 70, 80, 90, 100])
    ax.set_yticklabels(["60", "70", "80", "90", "100"], color='white')
    ax.plot(angles, values, color=color_hex, linewidth=2)
    ax.fill(angles, values, color=color_hex, alpha=0.4)
    return fig