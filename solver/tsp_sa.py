"""
焼きなまし法（Simulated Annealing）による TSP 近似解法

初期解に貪欲法（最近傍法）を使い、
2-opt swap を近傍操作として焼きなまし法で最適化する。
"""

import time
import math
import random
import numpy as np
from utils.distance import total_distance
from solver.tsp_greedy2opt import greedy_nearest_neighbor


def solve_tsp_sa(
    dist_matrix: np.ndarray,
    start_index: int = 0,
    initial_temp: float = 1000.0,
    cooling_rate: float = 0.995,
    min_temp: float = 1e-3,
    max_iter_per_temp: int = 100,
    seed: int = 42,
) -> dict:
    """
    焼きなまし法でTSPを解く

    近傍操作: ランダムに2点を選び、その間のルートを逆順にする（2-opt swap）

    Parameters
    ----------
    dist_matrix : np.ndarray
        距離行列 (km)
    start_index : int
        出発地点のインデックス
    initial_temp : float
        初期温度
    cooling_rate : float
        冷却率（0 < cooling_rate < 1）
    min_temp : float
        終了温度（これを下回ったら終了）
    max_iter_per_temp : int
        各温度でのイテレーション数
    seed : int
        乱数シード

    Returns
    -------
    dict
        route        : list[int]   最終ルート
        total_dist   : float       総距離 (km)
        elapsed_sec  : float       計算時間 (秒)
        status       : str         "Feasible"固定
        history      : list[float] 各温度ステップでの最良距離（収束グラフ用）
    """
    random.seed(seed)
    np.random.seed(seed)
    n = len(dist_matrix)
    t0 = time.perf_counter()

    # 初期解: 貪欲法（最近傍法）
    current_route = greedy_nearest_neighbor(dist_matrix, start_index)
    current_dist = total_distance(current_route, dist_matrix)

    best_route = current_route[:]
    best_dist = current_dist

    temp = initial_temp
    history = [best_dist]  # 収束グラフ用

    # -----------------------------------------------
    # 焼きなまし法のメインループ
    # -----------------------------------------------
    while temp > min_temp:
        for _ in range(max_iter_per_temp):
            # 近傍解の生成: ランダムな2点間を逆順にする
            i = random.randint(1, n - 2)
            j = random.randint(i + 1, n - 1)
            new_route = current_route[:i] + current_route[i:j + 1][::-1] + current_route[j + 1:]
            new_dist = total_distance(new_route, dist_matrix)

            # 受理判定
            delta = new_dist - current_dist
            if delta < 0 or random.random() < math.exp(-delta / temp):
                current_route = new_route
                current_dist = new_dist

                # 全体最良解の更新
                if current_dist < best_dist:
                    best_route = current_route[:]
                    best_dist = current_dist

        # 冷却
        temp *= cooling_rate
        history.append(best_dist)

    elapsed = time.perf_counter() - t0

    return {
        "route": best_route,
        "total_dist": best_dist,
        "elapsed_sec": elapsed,
        "status": "Feasible",
        "history": history,
    }