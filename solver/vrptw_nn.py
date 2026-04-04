"""
時間窓考慮版 Nearest Neighbor による VRPTW 近似解法

最近傍法を時間窓制約に対応させた構築型ヒューリスティクス。
OR-Toolsの初期解探索を補助する役割と、
単独でのベースライン解生成の両方に使える。

アルゴリズムの流れ:
1. 各車両がデポから出発
2. 現在地から「訪問可能かつ最も近い」未訪問顧客を選択
   （時間窓・容量制約を満たすもの）
3. 訪問可能な顧客がなくなったらデポに戻り、次の車両へ
4. 全顧客訪問済みまたは全車両使用済みで終了
"""

import time
import numpy as np


def _arrival_time(
    current_node: int,
    next_node: int,
    current_time: int,
    time_matrix: np.ndarray,
    time_windows: list[tuple[int, int]],
    service_times: list[int],
) -> int | None:
    """
    next_nodeへの到着時刻を計算する。
    時間窓に間に合わない場合はNoneを返す。

    待機（早着）は許容する（時間窓のearliest以前に着いたら待つ）。
    """
    travel = int(time_matrix[current_node][next_node])
    arrive = current_time + travel

    earliest, latest = time_windows[next_node]

    # 最遅到着時刻を超える場合は訪問不可
    if arrive > latest:
        return None

    # 早着の場合は待機（earliest まで待つ）
    return max(arrive, earliest)


def solve_vrptw_nn(
    dist_matrix: np.ndarray,
    demands: list[int],
    vehicle_capacities: list[int],
    time_windows: list[tuple[int, int]],
    service_times: list[int],
    depot: int = 0,
    speed_kmh: float = 60.0,
) -> dict:
    """
    時間窓考慮版 Nearest Neighbor で VRPTW を解く

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
        status         : str               "Feasible"固定（解なし時は"No solution"）
    """
    t0 = time.perf_counter()

    # 距離→移動時間（分）に変換
    time_matrix = (dist_matrix / speed_kmh * 60)

    num_vehicles = len(vehicle_capacities)
    unvisited = set(i for i in range(len(dist_matrix)) if i != depot)

    routes = []
    arrival_times_all = []
    vehicle_dist = []
    vehicle_load = []

    for v in range(num_vehicles):
        if not unvisited:
            break

        capacity = vehicle_capacities[v]
        route = [depot]
        arrivals = [time_windows[depot][0]]  # デポ出発時刻
        current = depot
        current_time = time_windows[depot][0]
        current_load = 0
        dist = 0

        while unvisited:
            # 訪問可能な顧客を探す（容量・時間窓の両方を満たすもの）
            best_node = None
            best_dist = float("inf")
            best_arrival = None

            for node in unvisited:
                # 容量チェック
                if current_load + demands[node] > capacity:
                    continue

                # 時間窓チェック
                arr = _arrival_time(
                    current, node, current_time,
                    time_matrix, time_windows, service_times
                )
                if arr is None:
                    continue

                # デポへ帰着できるかチェック
                depart_from_node = arr + service_times[node]
                arr_depot = depart_from_node + int(time_matrix[node][depot])
                if arr_depot > time_windows[depot][1]:
                    continue

                # 最近傍を選択
                d = dist_matrix[current][node]
                if d < best_dist:
                    best_dist = d
                    best_node = node
                    best_arrival = arr

            if best_node is None:
                break

            # 顧客を訪問
            route.append(best_node)
            arrivals.append(best_arrival)
            dist += dist_matrix[current][best_node]
            current_load += demands[best_node]
            current_time = best_arrival + service_times[best_node]
            current = best_node
            unvisited.remove(best_node)

        # デポに戻る
        route.append(depot)
        depot_arrival = current_time + int(time_matrix[current][depot])
        arrivals.append(depot_arrival)
        dist += dist_matrix[current][depot]

        routes.append(route)
        arrival_times_all.append(arrivals)
        vehicle_dist.append(dist)
        vehicle_load.append(current_load)

    elapsed = time.perf_counter() - t0

    # 未訪問顧客が残っている場合は解なし
    if unvisited:
        return {
            "routes": routes,
            "arrival_times": arrival_times_all,
            "total_dist": float("inf"),
            "vehicle_dist": vehicle_dist,
            "vehicle_load": vehicle_load,
            "elapsed_sec": elapsed,
            "status": "No solution (unvisited customers remain)",
        }

    return {
        "routes": routes,
        "arrival_times": arrival_times_all,
        "total_dist": sum(vehicle_dist),
        "vehicle_dist": vehicle_dist,
        "vehicle_load": vehicle_load,
        "elapsed_sec": elapsed,
        "status": "Feasible",
    }