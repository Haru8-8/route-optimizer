"""
貪欲法 + 2-opt による TSP 近似解法

1. 貪欲法で初期解を構築（最近傍法）
2. 2-opt で局所最適化
"""

import time
import numpy as np
from utils.distance import total_distance


# -----------------------------------------------
# 貪欲法（最近傍法）
# -----------------------------------------------

def greedy_nearest_neighbor(
    dist_matrix: np.ndarray,
    start_index: int = 0,
) -> list[int]:
    """
    最近傍法で初期ルートを構築する

    未訪問の地点の中から最も近い地点を順番に選ぶ。

    Parameters
    ----------
    dist_matrix : np.ndarray
        距離行列
    start_index : int
        出発地点のインデックス

    Returns
    -------
    list[int]
        ルート（インデックスのリスト）
    """
    n = len(dist_matrix)
    visited = [False] * n
    route = [start_index]
    visited[start_index] = True

    for _ in range(n - 1):
        current = route[-1]
        # 未訪問の地点の中で最も近いものを選ぶ
        nearest = -1
        nearest_dist = float("inf")
        for j in range(n):
            if not visited[j] and dist_matrix[current][j] < nearest_dist:
                nearest = j
                nearest_dist = dist_matrix[current][j]
        route.append(nearest)
        visited[nearest] = True

    return route


# -----------------------------------------------
# 2-opt 局所探索
# -----------------------------------------------

def two_opt(
    route: list[int],
    dist_matrix: np.ndarray,
    max_iter: int = 1000,
) -> list[int]:
    """
    2-opt でルートを局所最適化する

    2本のエッジを選んで交差を解消する操作を、
    改善がなくなるまで繰り返す。

    Parameters
    ----------
    route : list[int]
        初期ルート
    dist_matrix : np.ndarray
        距離行列
    max_iter : int
        最大イテレーション数

    Returns
    -------
    list[int]
        改善後のルート
    """
    best_route = route[:]
    best_dist = total_distance(best_route, dist_matrix)
    n = len(route)

    for _ in range(max_iter):
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                # エッジ (i-1, i) と (j, j+1) を
                # エッジ (i-1, j) と (i, j+1) に置き換える
                new_route = best_route[:i] + best_route[i:j + 1][::-1] + best_route[j + 1:]
                new_dist = total_distance(new_route, dist_matrix)
                if new_dist < best_dist - 1e-10:
                    best_route = new_route
                    best_dist = new_dist
                    improved = True
        if not improved:
            break

    return best_route


# -----------------------------------------------
# 貪欲法 + 2-opt のメイン関数
# -----------------------------------------------

def solve_tsp_greedy2opt(
    dist_matrix: np.ndarray,
    start_index: int = 0,
) -> dict:
    """
    貪欲法（最近傍法）+ 2-opt でTSPを解く

    Parameters
    ----------
    dist_matrix : np.ndarray
        距離行列 (km)
    start_index : int
        出発地点のインデックス

    Returns
    -------
    dict
        route       : list[int]  ルート（インデックスのリスト）
        total_dist  : float      総距離 (km)
        elapsed_sec : float      計算時間 (秒)
        status      : str        "Feasible"固定
    """
    t0 = time.perf_counter()

    # Step 1: 貪欲法で初期解を構築
    initial_route = greedy_nearest_neighbor(dist_matrix, start_index)

    # Step 2: 2-opt で局所最適化
    optimized_route = two_opt(initial_route, dist_matrix)

    elapsed = time.perf_counter() - t0
    dist = total_distance(optimized_route, dist_matrix)

    return {
        "route": optimized_route,
        "total_dist": dist,
        "elapsed_sec": elapsed,
        "status": "Feasible",
    }