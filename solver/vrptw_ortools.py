"""
OR-Tools による VRPTW 厳密解法

時間窓付き車両ルーティング問題（VRPTW）を解く。
各顧客への訪問時間帯（時間窓）の制約を満たしながら
総移動距離を最小化する。
"""

import time
import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp


def solve_vrptw_ortools(
    dist_matrix: np.ndarray,
    demands: list[int],
    vehicle_capacities: list[int],
    time_windows: list[tuple[int, int]],
    service_times: list[int],
    depot: int = 0,
    time_limit_sec: int = 30,
    speed_kmh: float = 60.0,
) -> dict:
    """
    OR-Tools で VRPTW を解く

    Parameters
    ----------
    dist_matrix : np.ndarray
        距離行列 (km)
    demands : list[int]
        各地点の需要量（デポは0）
    vehicle_capacities : list[int]
        各車両の容量
    time_windows : list[tuple[int, int]]
        各地点の時間窓 (earliest, latest) 単位：分
    service_times : list[int]
        各地点のサービス時間（分）
    depot : int
        デポのインデックス
    time_limit_sec : int
        タイムリミット（秒）
    speed_kmh : float
        車両の平均速度 (km/h)

    Returns
    -------
    dict
        routes         : list[list[int]]   各車両のルート
        arrival_times  : list[list[int]]   各車両の各地点への到着時刻（分）
        total_dist     : float             総距離 (km)
        vehicle_dist   : list[float]       各車両の走行距離
        vehicle_load   : list[int]         各車両の積載量
        elapsed_sec    : float             計算時間（秒）
        status         : str               求解ステータス
    """
    n = len(dist_matrix)
    num_vehicles = len(vehicle_capacities)

    # 距離→移動時間（分）に変換
    time_matrix = (dist_matrix / speed_kmh * 60).astype(int)

    # -----------------------------------------------
    # データモデルの作成
    # -----------------------------------------------
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(dist_matrix[from_node][to_node] * 1000)

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(time_matrix[from_node][to_node] + service_times[from_node])

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return demands[from_node]

    manager = pywrapcp.RoutingIndexManager(n, num_vehicles, int(depot))
    routing = pywrapcp.RoutingModel(manager)

    # 距離コールバック（コスト最小化）
    dist_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(dist_callback_index)

    # 時間次元（時間窓制約）
    time_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.AddDimension(
        time_callback_index,
        60,    # 待機可能時間（分）
        1440,  # 最大時刻（24時間=1440分）
        False, # 累積時間をゼロから始めない（デポの開始時刻を考慮）
        "Time",
    )
    time_dimension = routing.GetDimensionOrDie("Time")

    # 各地点の時間窓を設定
    for node in range(n):
        index = manager.NodeToIndex(node)
        time_dimension.CumulVar(index).SetRange(
            time_windows[node][0],
            time_windows[node][1],
        )

    # デポの時間窓を各車両の開始・終了に設定
    for v in range(num_vehicles):
        start_index = routing.Start(v)
        end_index = routing.End(v)
        time_dimension.CumulVar(start_index).SetRange(
            time_windows[depot][0],
            time_windows[depot][1],
        )
        time_dimension.CumulVar(end_index).SetRange(
            time_windows[depot][0],
            time_windows[depot][1],
        )

    # 容量制約
    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,
        vehicle_capacities,
        True,
        "Capacity",
    )

    # -----------------------------------------------
    # 探索パラメータ
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
            "arrival_times": [],
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
    arrival_times = []
    vehicle_dist = []
    vehicle_load = []

    for v in range(num_vehicles):
        route = []
        arrivals = []
        index = routing.Start(v)
        dist = 0
        load = 0
        prev_index = index

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            route.append(node)
            load += demands[node]
            t = solution.Min(time_dimension.CumulVar(index))
            arrivals.append(t)
            index = solution.Value(routing.NextVar(index))
            dist += dist_matrix[manager.IndexToNode(prev_index)][manager.IndexToNode(index)]
            prev_index = index

        # デポへの帰着
        node = manager.IndexToNode(index)
        route.append(node)
        t = solution.Min(time_dimension.CumulVar(index))
        arrivals.append(t)

        routes.append(route)
        arrival_times.append(arrivals)
        vehicle_dist.append(dist)
        vehicle_load.append(load)

    total_dist = sum(vehicle_dist)
    status = "Optimal" if routing.status() == 1 else "Feasible"

    return {
        "routes": routes,
        "arrival_times": arrival_times,
        "total_dist": total_dist,
        "vehicle_dist": vehicle_dist,
        "vehicle_load": vehicle_load,
        "elapsed_sec": elapsed,
        "status": status,
    }