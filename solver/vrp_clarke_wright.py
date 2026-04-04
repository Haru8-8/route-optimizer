"""
Clarke-Wright 節約法による VRP 近似解法

「2台の車両のルートを1台に統合すると何km節約できるか」を
節約量の大きい順に統合していく構築型ヒューリスティクス。

参考: Clarke, G. & Wright, J.W. (1964).
      Scheduling of Vehicles from a Central Depot to a Number of Delivery Points.
"""

import time
import numpy as np


def _calc_savings(dist_matrix: np.ndarray, depot: int, customers: list) -> list:
    """
    各顧客ペアの節約量を計算する

    節約量 S(i,j) = d(depot,i) + d(depot,j) - d(i,j)
    """
    savings = []
    for idx, i in enumerate(customers):
        for j in customers[idx + 1:]:
            s = (
                dist_matrix[depot][i]
                + dist_matrix[depot][j]
                - dist_matrix[i][j]
            )
            savings.append((s, i, j))
    savings.sort(reverse=True)
    return savings


def solve_vrp_clarke_wright(
    dist_matrix: np.ndarray,
    demands: list,
    vehicle_capacities: list,
    depot: int = 0,
) -> dict:
    """
    Clarke-Wright 節約法で VRP を解く

    全車両同一容量を想定（vehicle_capacities の最初の値を使用）。

    Returns
    -------
    dict
        routes       : list[list[int]]  各車両のルート
        total_dist   : float            総距離 (km)
        vehicle_dist : list[float]      各車両の走行距離
        vehicle_load : list[int]        各車両の積載量
        elapsed_sec  : float            計算時間 (秒)
        status       : str              求解ステータス
    """
    t0 = time.perf_counter()
    capacity = vehicle_capacities[0]
    num_vehicles = len(vehicle_capacities)
    customers = [i for i in range(len(dist_matrix)) if i != depot]

    # 事前チェック：単体で容量を超える顧客がいれば即No solution
    for c in customers:
        if demands[c] > capacity:
            elapsed = time.perf_counter() - t0
            return {
                "routes": [],
                "total_dist": float("inf"),
                "vehicle_dist": [],
                "vehicle_load": [],
                "elapsed_sec": elapsed,
                "status": "No solution",
            }

    # -----------------------------------------------
    # Step 1: 初期解（各顧客を独立した1台の車両で訪問）
    # ルートをインデックスで管理して同一性を保証する
    # route_loads[k] = ルートkの積載量
    # route_list[k]  = ルートkの地点リスト [depot, ..., depot]
    # customer_to_route[c] = 顧客cが属するルートインデックスk
    # -----------------------------------------------
    route_list = [[depot, c, depot] for c in customers]
    route_loads = [demands[c] for c in customers]
    customer_to_route = {c: idx for idx, c in enumerate(customers)}

    # -----------------------------------------------
    # Step 2: 節約量の大きい順にルートを統合
    # -----------------------------------------------
    savings = _calc_savings(dist_matrix, depot, customers)

    for _, i, j in savings:
        ri = customer_to_route.get(i)
        rj = customer_to_route.get(j)

        # どちらかが既に統合済み（None）またはすでに同じルート
        if ri is None or rj is None or ri == rj:
            continue

        route_i = route_list[ri]
        route_j = route_list[rj]

        # 容量チェック
        new_load = route_loads[ri] + route_loads[rj]
        if new_load > capacity:
            continue

        # 統合可能条件：
        # iがroute_iの末尾顧客（route_i[-2]==i）かつjがroute_jの先頭顧客（route_j[1]==j）
        # またはその4パターン
        i_is_tail = route_i[-2] == i
        j_is_head = route_j[1] == j
        j_is_tail = route_j[-2] == j
        i_is_head = route_i[1] == i

        if i_is_tail and j_is_head:
            new_route = route_i[:-1] + route_j[1:]
        elif j_is_tail and i_is_head:
            new_route = route_j[:-1] + route_i[1:]
        elif i_is_tail and j_is_tail:
            new_route = route_i[:-1] + list(reversed(route_j[1:-1])) + [depot]
        elif i_is_head and j_is_head:
            new_route = [depot] + list(reversed(route_i[1:-1])) + route_j[1:]
        else:
            continue

        # 統合を適用: riのスロットに新ルートを入れ、rjをNoneで無効化
        route_list[ri] = new_route
        route_loads[ri] = new_load
        route_list[rj] = None
        route_loads[rj] = None

        # customer_to_route を更新（route_j内の顧客をriに付け替え）
        for node in new_route:
            if node != depot:
                customer_to_route[node] = ri

    elapsed = time.perf_counter() - t0

    # -----------------------------------------------
    # 有効なルートのみ抽出
    # -----------------------------------------------
    routes = [r for r in route_list if r is not None]
    loads = [route_loads[i] for i, r in enumerate(route_list) if r is not None]

    # -----------------------------------------------
    # 結果の集計
    # -----------------------------------------------
    vehicle_dist = []
    vehicle_load = []
    for route, load in zip(routes, loads):
        dist = sum(dist_matrix[route[k]][route[k + 1]] for k in range(len(route) - 1))
        vehicle_dist.append(dist)
        vehicle_load.append(load)

    # ステータス設定
    status = "Feasible"

    return {
        "routes": routes,
        "total_dist": sum(vehicle_dist),
        "vehicle_dist": vehicle_dist,
        "vehicle_load": vehicle_load,
        "elapsed_sec": elapsed,
        "status": status,
    }