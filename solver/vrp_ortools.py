"""
OR-Tools による VRP 厳密解法

容量制約付き車両ルーティング問題（CVRP）を解く。
デポから出発した複数の車両が顧客を訪問して戻る最短ルートを求める。
"""

import time
import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp


def solve_vrp_ortools(
    dist_matrix: np.ndarray,
    demands: list[int],
    vehicle_capacities: list[int],
    depot: int = 0,
    time_limit_sec: int = 30,
) -> dict:
    """
    OR-Tools で VRP を解く

    Parameters
    ----------
    dist_matrix : np.ndarray
        距離行列 (km)
    demands : list[int]
        各地点の需要量（デポは0）
    vehicle_capacities : list[int]
        各車両の容量（車両数 = len(vehicle_capacities)）
    depot : int
        デポのインデックス
    time_limit_sec : int
        タイムリミット（秒）

    Returns
    -------
    dict
        routes       : list[list[int]]  各車両のルート（インデックスのリスト）
        total_dist   : float            総距離 (km)
        vehicle_dist : list[float]      各車両の走行距離 (km)
        vehicle_load : list[int]        各車両の積載量
        elapsed_sec  : float            計算時間 (秒)
        status       : str              求解ステータス
    """
    n = len(dist_matrix)
    num_vehicles = len(vehicle_capacities)
    scale = 1000  # OR-Toolsは整数距離を要求するため1000倍

    dist_matrix_int = (dist_matrix * scale).astype(int)

    # -----------------------------------------------
    # データモデルの作成
    # -----------------------------------------------
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return dist_matrix_int[from_node][to_node]

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return demands[from_node]

    manager = pywrapcp.RoutingIndexManager(n, num_vehicles, int(depot))
    routing = pywrapcp.RoutingModel(manager)

    # 距離コールバックの登録
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # 容量制約の追加
    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,                   # slack（余裕）なし
        vehicle_capacities,  # 各車両の容量
        True,                # 容量の累積をゼロから始める
        "Capacity",
    )

    # -----------------------------------------------
    # 探索パラメータの設定
    # -----------------------------------------------
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = time_limit_sec

    # -----------------------------------------------
    # 求解
    # -----------------------------------------------
    t0 = time.perf_counter()
    solution = routing.SolveWithParameters(search_parameters)
    elapsed = time.perf_counter() - t0

    if not solution:
        return {
            "routes": [],
            "total_dist": float("inf"),
            "vehicle_dist": [],
            "vehicle_load": [],
            "elapsed_sec": elapsed,
            "status": "No solution",
        }

    # -----------------------------------------------
    # 結果の取り出し
    # -----------------------------------------------
    routes = []
    vehicle_dist = []
    vehicle_load = []

    for v in range(num_vehicles):
        route = []
        index = routing.Start(v)
        load = 0
        dist = 0
        prev_index = index

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            route.append(node)
            load += demands[node]
            index = solution.Value(routing.NextVar(index))
            dist += dist_matrix[manager.IndexToNode(prev_index)][manager.IndexToNode(index)]
            prev_index = index

        # 最後にデポへ戻る
        route.append(depot)
        routes.append(route)
        vehicle_dist.append(dist)
        vehicle_load.append(load)

    total_dist = sum(vehicle_dist)
    status = "Optimal" if routing.status() == 1 else "Feasible"

    return {
        "routes": routes,
        "total_dist": total_dist,
        "vehicle_dist": vehicle_dist,
        "vehicle_load": vehicle_load,
        "elapsed_sec": elapsed,
        "status": status,
    }