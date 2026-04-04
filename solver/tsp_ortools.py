"""
OR-Tools による TSP 厳密解法

Google OR-Tools の Routing Library を使い、
厳密解（または制限時間内の最良解）を求める。
"""

import time
import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp


def solve_tsp_ortools(
    dist_matrix: np.ndarray,
    start_index: int = 0,
    time_limit_sec: int = 10,
) -> dict:
    """
    OR-Tools でTSPを解く

    Parameters
    ----------
    dist_matrix : np.ndarray
        距離行列 (km)
    start_index : int
        出発地点のインデックス
    time_limit_sec : int
        タイムリミット（秒）

    Returns
    -------
    dict
        route       : list[int]  最適ルート（インデックスのリスト）
        total_dist  : float      総距離 (km)
        elapsed_sec : float      計算時間 (秒)
        status      : str        求解ステータス
    """
    n = len(dist_matrix)

    # OR-Tools は整数の距離行列を要求するため1000倍してmに変換
    scale = 1000
    dist_matrix_int = (dist_matrix * scale).astype(int)

    # データモデルの作成
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return dist_matrix_int[from_node][to_node]

    manager = pywrapcp.RoutingIndexManager(n, 1, int(start_index))
    routing = pywrapcp.RoutingModel(manager)

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # 探索パラメータの設定
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = time_limit_sec

    # 求解
    t0 = time.perf_counter()
    solution = routing.SolveWithParameters(search_parameters)
    elapsed = time.perf_counter() - t0

    # 結果の取り出し
    if solution:
        route = []
        index = routing.Start(0)
        while not routing.IsEnd(index):
            route.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))

        total_dist = solution.ObjectiveValue() / scale
        status = "Feasible" if routing.status() in (1,2) else "No solution"
    else:
        # 解なし（地点数が少なければほぼ起きない）
        route = list(range(n))
        total_dist = float("inf")
        status = "No solution"

    return {
        "route": route,
        "total_dist": total_dist,
        "elapsed_sec": elapsed,
        "status": status,
    }