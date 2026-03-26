"""
距離計算ユーティリティ

緯度経度からHaversine公式で実距離（km）を計算し、
距離行列を生成する。
"""

import numpy as np


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    2点間のHaversine距離を返す（単位: km）

    Parameters
    ----------
    lat1, lon1 : float
        地点1の緯度・経度（度数法）
    lat2, lon2 : float
        地点2の緯度・経度（度数法）

    Returns
    -------
    float
        2点間の距離 (km)
    """
    R = 6371.0  # 地球半径 (km)

    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)

    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return R * c


def build_distance_matrix(coords: list[tuple[float, float]]) -> np.ndarray:
    """
    座標リストから距離行列を生成する

    Parameters
    ----------
    coords : list of (lat, lon)
        地点の緯度・経度リスト

    Returns
    -------
    np.ndarray
        shape (n, n) の距離行列（単位: km）
    """
    n = len(coords)
    matrix = np.zeros((n, n))

    for i in range(n):
        for j in range(i + 1, n):
            d = haversine(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
            matrix[i][j] = d
            matrix[j][i] = d

    return matrix


def total_distance(route: list[int], dist_matrix: np.ndarray) -> float:
    """
    ルートの総距離を計算する（出発地点に戻る周回距離）

    Parameters
    ----------
    route : list of int
        地点のインデックスリスト（出発地点から順番）
    dist_matrix : np.ndarray
        距離行列

    Returns
    -------
    float
        総距離 (km)
    """
    total = 0.0
    n = len(route)
    for i in range(n):
        total += dist_matrix[route[i]][route[(i + 1) % n]]
    return total