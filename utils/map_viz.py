"""
地図可視化ユーティリティ

Foliumを使ってルートを地図上に描画する。
TSP・VRP・VRPTWの各問題に対応。
"""

import folium
import pandas as pd


# アルゴリズムごとの色定義（TSP用）
ALGO_COLORS = {
    "OR-Tools":      "#2196F3",  # 青
    "貪欲法+2-opt":  "#4CAF50",  # 緑
    "SA":            "#FF5722",  # オレンジレッド
}

DEFAULT_COLOR = "#9C27B0"  # 紫（フォールバック）

# 車両ごとの色定義（VRP・VRPTW用・最大10台）
VEHICLE_COLORS = [
    "#2196F3",  # 青
    "#F44336",  # 赤
    "#4CAF50",  # 緑
    "#FF9800",  # オレンジ
    "#9C27B0",  # 紫
    "#00BCD4",  # シアン
    "#E91E63",  # ピンク
    "#795548",  # ブラウン
    "#607D8B",  # グレー
    "#FFEB3B",  # 黄
]


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


def build_vrp_map(
    df: pd.DataFrame,
    routes: list,
    depot_index: int = 0,
    zoom_start: int = 10,
    arrival_times: list = None,
    time_windows: list = None,
) -> folium.Map:
    """
    VRP・VRPTWのルートをFolium地図上に描画する

    車両ごとに異なる色でルートを描画する。

    Parameters
    ----------
    df : pd.DataFrame
        columns: type, name, lat, lon
    routes : list[list[int]]
        各車両のルート（インデックスのリスト）
    depot_index : int
        デポのインデックス
    zoom_start : int
        初期ズームレベル
    arrival_times : list[list[int]] | None
        各車両の各地点への到着時刻（分）
    time_windows : list[tuple[int, int]] | None
        各地点の時間窓

    Returns
    -------
    folium.Map
    """
    center_lat = df["lat"].mean()
    center_lon = df["lon"].mean()

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles="OpenStreetMap",
    )

    # デポのマーカー
    depot_row = df.iloc[depot_index]
    folium.Marker(
        location=[depot_row["lat"], depot_row["lon"]],
        popup=folium.Popup(f"<b>🏭 デポ: {depot_row['name']}</b>", max_width=200),
        tooltip=f"🏭 {depot_row['name']}",
        icon=folium.Icon(color="black", icon="home", prefix="fa"),
    ).add_to(m)

    # 各車両のルートを描画
    for v_idx, route in enumerate(routes):
        if len(route) <= 2:
            continue

        color = VEHICLE_COLORS[v_idx % len(VEHICLE_COLORS)]
        vehicle_label = f"車両{v_idx + 1}"

        # ルート線
        route_coords = [[df.iloc[idx]["lat"], df.iloc[idx]["lon"]] for idx in route]
        folium.PolyLine(
            locations=route_coords,
            color=color,
            weight=3,
            opacity=0.8,
            tooltip=vehicle_label,
        ).add_to(m)

        # 顧客マーカー
        for order, node_idx in enumerate(route):
            if node_idx == depot_index:
                continue

            row = df.iloc[node_idx]
            popup_lines = [f"<b>{vehicle_label} - {order}番目</b><br>{row['name']}"]

            if arrival_times is not None and v_idx < len(arrival_times):
                arr = arrival_times[v_idx][order]
                h, m_min = divmod(arr, 60)
                popup_lines.append(f"到着: {h:02d}:{m_min:02d}")

            if time_windows is not None:
                tw = time_windows[node_idx]
                s_h, s_m = divmod(tw[0], 60)
                e_h, e_m = divmod(tw[1], 60)
                popup_lines.append(f"時間窓: {s_h:02d}:{s_m:02d}〜{e_h:02d}:{e_m:02d}")

            popup_text = "<br>".join(popup_lines)

            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=8,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                popup=folium.Popup(popup_text, max_width=200),
                tooltip=f"{vehicle_label} {order}: {row['name']}",
            ).add_to(m)

    # 凡例
    legend_items = ""
    for v_idx, route in enumerate(routes):
        if len(route) <= 2:
            continue
        color = VEHICLE_COLORS[v_idx % len(VEHICLE_COLORS)]
        legend_items += (
            f'<div style="display:flex;align-items:center;gap:6px;margin:2px 0">'
            f'<div style="width:20px;height:4px;background:{color};border-radius:2px"></div>'
            f'<span>車両{v_idx + 1}</span></div>'
        )

    legend_html = f"""
    <div style="
        position: fixed;
        bottom: 10px; right: 10px;
        background-color: white;
        border: 1px solid #ccc;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 12px;
        z-index: 1000;
    ">
        {legend_items}
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m