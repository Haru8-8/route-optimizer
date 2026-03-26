"""
地図可視化ユーティリティ

Foliumを使ってルートを地図上に描画する。
"""

import folium
import pandas as pd


# アルゴリズムごとの色定義
ALGO_COLORS = {
    "OR-Tools":      "#2196F3",  # 青
    "貪欲法+2-opt":  "#4CAF50",  # 緑
    "SA":            "#FF5722",  # オレンジレッド
}

DEFAULT_COLOR = "#9C27B0"  # 紫（フォールバック）


def build_route_map(
    df: pd.DataFrame,
    route: list[int],
    algo_name: str = "OR-Tools",
    zoom_start: int = 10,
) -> folium.Map:
    """
    ルートをFolium地図上に描画して返す

    Parameters
    ----------
    df : pd.DataFrame
        columns: name, lat, lon
    route : list of int
        地点インデックスのリスト（出発地点から順番）
    algo_name : str
        アルゴリズム名（色分けに使用）
    zoom_start : int
        初期ズームレベル

    Returns
    -------
    folium.Map
    """
    # 地図の中心を計算
    center_lat = df["lat"].mean()
    center_lon = df["lon"].mean()

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles="OpenStreetMap",
    )

    color = ALGO_COLORS.get(algo_name, DEFAULT_COLOR)

    # ルート順に座標リストを作成（最後に出発地点へ戻る）
    route_coords = []
    for idx in route:
        row = df.iloc[idx]
        route_coords.append([row["lat"], row["lon"]])
    route_coords.append(route_coords[0])  # 出発地点に戻る

    # ルート線の描画
    folium.PolyLine(
        locations=route_coords,
        color=color,
        weight=3,
        opacity=0.8,
    ).add_to(m)

    # 地点マーカーの描画
    for order, idx in enumerate(route):
        row = df.iloc[idx]
        is_start = order == 0

        # 出発地点は星マーク、それ以外は番号付き円
        if is_start:
            icon = folium.Icon(color="red", icon="star", prefix="fa")
            popup_text = f"<b>🚩 出発: {row['name']}</b>"
        else:
            icon = folium.Icon(color="blue", icon="circle", prefix="fa")
            popup_text = f"<b>{order}. {row['name']}</b>"

        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=folium.Popup(popup_text, max_width=200),
            tooltip=f"{order if not is_start else '🚩'} {row['name']}",
            icon=icon,
        ).add_to(m)

    return m


def build_comparison_map(
    df: pd.DataFrame,
    route: list[int],
    algo_name: str,
    total_dist: float,
) -> folium.Map:
    """
    比較ページ用の地図（タイトル付き）

    Parameters
    ----------
    df : pd.DataFrame
        columns: name, lat, lon
    route : list of int
        地点インデックスのリスト
    algo_name : str
        アルゴリズム名
    total_dist : float
        総距離 (km)

    Returns
    -------
    folium.Map
    """
    m = build_route_map(df, route, algo_name, zoom_start=9)

    # 地図右下に総距離を表示
    legend_html = f"""
    <div style="
        position: fixed;
        bottom: 10px; right: 10px;
        background-color: white;
        border: 2px solid {ALGO_COLORS.get(algo_name, DEFAULT_COLOR)};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
        font-weight: bold;
        z-index: 1000;
    ">
        {algo_name}<br>
        {total_dist:.2f} km
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m