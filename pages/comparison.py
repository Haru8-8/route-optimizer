"""
アルゴリズム比較ページ

TSP・VRP・VRPTWのアルゴリズム比較をタブで切り替えて表示する。
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import streamlit as st
from streamlit_folium import st_folium

matplotlib.use("Agg")

# -----------------------------------------------
# 日本語フォント設定
# -----------------------------------------------
def _setup_japanese_font():
    import glob
    import platform
    from matplotlib import font_manager
    import matplotlib as mpl

    if platform.system() == "Darwin":
        for font_name in ["Hiragino Sans", "Hiragino Maru Gothic Pro", "AppleGothic"]:
            if any(font_name in f.name for f in font_manager.fontManager.ttflist):
                mpl.rcParams['font.family'] = font_name
                return
        for pattern in ['/System/Library/Fonts/**/Hiragino*.ttc', '/Library/Fonts/**/Hiragino*.ttc']:
            files = glob.glob(pattern, recursive=True)
            if files:
                font_manager.fontManager.addfont(files[0])
                prop = font_manager.FontProperties(fname=files[0])
                mpl.rcParams['font.family'] = prop.get_name()
                return

    font_manager._load_fontmanager(try_read_cache=False)
    for font in font_manager.fontManager.ttflist:
        if 'Noto' in font.name and 'CJK' in font.name:
            mpl.rcParams['font.family'] = font.name
            return

    for pattern in ['/usr/share/fonts/**/Noto*CJK*.ttc', '/usr/share/fonts/**/Noto*CJK*.otf']:
        files = glob.glob(pattern, recursive=True)
        if files:
            font_manager.fontManager.addfont(files[0])
            prop = font_manager.FontProperties(fname=files[0])
            mpl.rcParams['font.family'] = prop.get_name()
            return

_setup_japanese_font()

from utils.distance import build_distance_matrix
from utils.map_viz import build_comparison_map, build_vrp_map
from solver.tsp_ortools import solve_tsp_ortools
from solver.tsp_greedy2opt import solve_tsp_greedy2opt
from solver.tsp_sa import solve_tsp_sa
from solver.vrp_ortools import solve_vrp_ortools
from solver.vrp_clarke_wright import solve_vrp_clarke_wright
from solver.vrptw_ortools import solve_vrptw_ortools
from solver.vrptw_nn import solve_vrptw_nn

# -----------------------------------------------
# ページ設定
# -----------------------------------------------
st.set_page_config(
    page_title="アルゴリズム比較",
    page_icon="📊",
    layout="wide",
)

st.title("📊 アルゴリズム比較")
st.caption("ランダム生成した地点で各問題のアルゴリズムの性能を比較します。")

# -----------------------------------------------
# ランダムデータ生成ユーティリティ
# -----------------------------------------------
def generate_locations(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    lats = rng.uniform(35.3, 36.2, n)
    lons = rng.uniform(138.8, 140.5, n)
    names = [f"地点{i+1:02d}" for i in range(n)]
    return pd.DataFrame({"name": names, "lat": lats, "lon": lons})


def generate_vrp_data(n_customers: int, seed: int, max_demand: int = 20):
    """デポ+顧客のVRPデータを生成"""
    rng = np.random.default_rng(seed)
    lats = rng.uniform(35.3, 36.2, n_customers + 1)
    lons = rng.uniform(138.8, 140.5, n_customers + 1)
    names = ["デポ"] + [f"顧客{i+1:02d}" for i in range(n_customers)]
    types = ["depot"] + ["customer"] * n_customers
    demands = [0] + rng.integers(5, max_demand, n_customers).tolist()
    return pd.DataFrame({
        "type": types, "name": names,
        "lat": lats, "lon": lons, "demand": demands,
    })


def generate_vrptw_data(n_customers: int, seed: int, max_demand: int = 20):
    """デポ+顧客のVRPTWデータを生成"""
    rng = np.random.default_rng(seed)
    df = generate_vrp_data(n_customers, seed, max_demand)
    # 時間窓をランダムに生成（出発から0〜480分の範囲）
    starts = [0] + sorted(rng.integers(0, 360, n_customers).tolist())
    ends = [480] + [s + rng.integers(60, 180) for s in starts[1:]]
    service = [0] + rng.integers(10, 20, n_customers).tolist()
    df["time_window_start"] = starts
    df["time_window_end"] = ends
    df["service_time"] = service
    return df


# -----------------------------------------------
# タブ切り替え
# -----------------------------------------------
tab_tsp, tab_vrp, tab_vrptw = st.tabs(["🗺️ TSP比較", "🚛 VRP比較", "⏰ VRPTW比較"])

# =============================================
# TSP比較タブ
# =============================================
with tab_tsp:
    st.subheader("TSP アルゴリズム比較")
    st.caption("OR-Tools・貪欲法+2-opt・SAの性能を比較します。")

    c1, c2 = st.columns([2, 1])
    with c1:
        n_tsp = st.slider("地点数", 5, 50, 15, key="tsp_n")
    with c2:
        seed_tsp = st.number_input("乱数シード", 0, 9999, 42, key="tsp_seed")

    with st.expander("🔧 SA パラメータ"):
        initial_temp = st.slider("初期温度", 100.0, 5000.0, 1000.0, step=100.0, key="tsp_temp")
        cooling_rate = st.slider("冷却率", 0.900, 0.999, 0.995, step=0.001, format="%.3f", key="tsp_cool")

    if st.button("🚀 TSP比較を実行", type="primary", key="tsp_run"):
        df_tsp = generate_locations(n_tsp, seed_tsp)
        coords = list(zip(df_tsp["lat"], df_tsp["lon"]))
        dist_matrix = build_distance_matrix(coords)

        with st.spinner("3アルゴリズムを計算中..."):
            tsp_results = {
                "OR-Tools": solve_tsp_ortools(dist_matrix, start_index=0),
                "貪欲法+2-opt": solve_tsp_greedy2opt(dist_matrix, start_index=0),
                "SA": solve_tsp_sa(dist_matrix, start_index=0,
                                   initial_temp=initial_temp, cooling_rate=cooling_rate),
            }
        st.session_state["tsp_comp"] = tsp_results
        st.session_state["tsp_df"] = df_tsp
        st.session_state["tsp_dist"] = dist_matrix

    if "tsp_comp" in st.session_state:
        tsp_results = st.session_state["tsp_comp"]
        df_tsp = st.session_state["tsp_df"]
        ortools_dist = tsp_results["OR-Tools"]["total_dist"]

        # サマリーテーブル
        st.subheader("📋 結果サマリー")
        rows = []
        for algo, res in tsp_results.items():
            gap = "基準" if algo == "OR-Tools" else f"+{(res['total_dist'] - ortools_dist) / ortools_dist * 100:.1f}%"
            rows.append({
                "アルゴリズム": algo,
                "総距離 (km)": f"{res['total_dist']:.2f}",
                "計算時間 (秒)": f"{res['elapsed_sec']:.4f}",
                "OR-Toolsとの乖離": gap,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # 地図横並び
        st.subheader("🗺️ ルートの可視化")
        cols = st.columns(3)
        for col, (algo, res) in zip(cols, tsp_results.items()):
            with col:
                st.markdown(f"**{algo}**")
                m = build_comparison_map(df_tsp, res["route"], algo, res["total_dist"])
                st_folium(m, use_container_width=True, height=360, key=f"tsp_map_{algo}")

        # SA収束グラフ
        st.subheader("📈 SAの収束グラフ")
        sa_history = tsp_results["SA"].get("history", [])
        if sa_history:
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(sa_history, color="#FF5722", linewidth=1.5, label="SA 最良距離")
            ax.axhline(y=ortools_dist, color="#2196F3", linestyle="--", linewidth=1.5,
                       label=f"OR-Tools ({ortools_dist:.2f} km)")
            greedy_dist = tsp_results["貪欲法+2-opt"]["total_dist"]
            ax.axhline(y=greedy_dist, color="#4CAF50", linestyle="--", linewidth=1.5,
                       label=f"Greedy+2-opt ({greedy_dist:.2f} km)")
            ax.set_xlabel("Temperature Step")
            ax.set_ylabel("Distance (km)")
            ax.set_title("SA 収束グラフ")
            ax.legend()
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
            plt.close(fig)

# =============================================
# VRP比較タブ
# =============================================
with tab_vrp:
    st.subheader("VRP アルゴリズム比較")
    st.caption("OR-Tools と Clarke-Wright節約法の性能を比較します。")

    c1, c2, c3 = st.columns(3)
    with c1:
        n_vrp = st.slider("顧客数", 5, 30, 10, key="vrp_n")
    with c2:
        seed_vrp = st.number_input("乱数シード", 0, 9999, 42, key="vrp_seed")
    with c3:
        vrp_vehicles = st.slider("最大使用台数", 2, 8, 3, key="vrp_vehicles")

    vrp_capacity = st.slider("車両容量", 20, 200, 60, step=5, key="vrp_cap")

    if st.button("🚀 VRP比較を実行", type="primary", key="vrp_run"):
        df_vrp = generate_vrp_data(n_vrp, seed_vrp)
        coords = list(zip(df_vrp["lat"], df_vrp["lon"]))
        dist_matrix = build_distance_matrix(coords)
        demands = df_vrp["demand"].astype(int).tolist()
        capacities = [vrp_capacity] * vrp_vehicles
        depot_idx = 0

        with st.spinner("2アルゴリズムを計算中..."):
            vrp_results = {
                "OR-Tools": solve_vrp_ortools(dist_matrix, demands, capacities, depot_idx),
                "Clarke-Wright": solve_vrp_clarke_wright(dist_matrix, demands, capacities, depot_idx),
            }
        st.session_state["vrp_comp"] = vrp_results
        st.session_state["vrp_comp_df"] = df_vrp
        st.session_state["vrp_comp_cap"] = vrp_capacity
        st.session_state["vrp_comp_max"] = vrp_vehicles

    if "vrp_comp" in st.session_state:
        vrp_results = st.session_state["vrp_comp"]
        df_vrp = st.session_state["vrp_comp_df"]
        cap = st.session_state["vrp_comp_cap"]
        max_v = st.session_state.get("vrp_comp_max", vrp_vehicles)
        depot_idx = 0
        ortools_dist = vrp_results["OR-Tools"]["total_dist"]

        # サマリーテーブル
        st.subheader("📋 結果サマリー")
        rows = []
        for algo, res in vrp_results.items():
            gap = "基準" if algo == "OR-Tools" else f"+{(res['total_dist'] - ortools_dist) / ortools_dist * 100:.1f}%"
            used = sum(1 for r in res["routes"] if len(r) > 2)
            rows.append({
                "アルゴリズム": algo,
                "総距離 (km)": f"{res['total_dist']:.2f}",
                "使用台数 / 最大台数": f"{used} / {max_v} 台",
                "計算時間 (秒)": f"{res['elapsed_sec']:.4f}",
                "OR-Toolsとの乖離": gap,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # 各車両の積載量
        st.subheader("🚛 車両別積載量")
        load_rows = []
        for algo, res in vrp_results.items():
            for v_idx, (route, load, dist) in enumerate(
                zip(res["routes"], res["vehicle_load"], res["vehicle_dist"])
            ):
                if len(route) <= 2:
                    continue
                load_rows.append({
                    "アルゴリズム": algo,
                    "車両": f"車両{v_idx+1}",
                    "積載量": f"{load} / {cap}",
                    "走行距離 (km)": f"{dist:.2f}",
                    "訪問顧客数": len(route) - 2,
                })
        st.dataframe(pd.DataFrame(load_rows), use_container_width=True, hide_index=True)

        # 地図横並び
        st.subheader("🗺️ ルートの可視化")
        cols = st.columns(2)
        for col, (algo, res) in zip(cols, vrp_results.items()):
            with col:
                st.markdown(f"**{algo}**  \n総距離: {res['total_dist']:.2f} km")
                m = build_vrp_map(df_vrp, res["routes"], depot_idx)
                st_folium(m, use_container_width=True, height=420, key=f"vrp_comp_map_{algo}")

# =============================================
# VRPTW比較タブ
# =============================================
with tab_vrptw:
    st.subheader("VRPTW アルゴリズム比較")
    st.caption("OR-Tools と Nearest Neighbor（時間窓考慮版）の性能を比較します。")

    c1, c2, c3 = st.columns(3)
    with c1:
        n_vrptw = st.slider("顧客数", 5, 20, 8, key="vrptw_n")
    with c2:
        seed_vrptw = st.number_input("乱数シード", 0, 9999, 42, key="vrptw_seed")
    with c3:
        vrptw_vehicles = st.slider("最大使用台数", 2, 8, 3, key="vrptw_vehicles")

    c1, c2 = st.columns(2)
    with c1:
        vrptw_capacity = st.slider("車両容量", 20, 200, 60, step=5, key="vrptw_cap")
    with c2:
        vrptw_speed = st.slider("平均速度 (km/h)", 20, 120, 60, step=5, key="vrptw_speed")

    if st.button("🚀 VRPTW比較を実行", type="primary", key="vrptw_run"):
        df_vrptw = generate_vrptw_data(n_vrptw, seed_vrptw)
        coords = list(zip(df_vrptw["lat"], df_vrptw["lon"]))
        dist_matrix = build_distance_matrix(coords)
        demands = df_vrptw["demand"].astype(int).tolist()
        capacities = [vrptw_capacity] * vrptw_vehicles
        time_windows = list(zip(
            df_vrptw["time_window_start"].astype(int),
            df_vrptw["time_window_end"].astype(int),
        ))
        service_times = df_vrptw["service_time"].astype(int).tolist()
        depot_idx = 0

        with st.spinner("2アルゴリズムを計算中..."):
            vrptw_results = {
                "OR-Tools": solve_vrptw_ortools(
                    dist_matrix, demands, capacities,
                    time_windows, service_times, depot_idx,
                    speed_kmh=float(vrptw_speed),
                ),
                "Nearest Neighbor": solve_vrptw_nn(
                    dist_matrix, demands, capacities,
                    time_windows, service_times, depot_idx,
                    speed_kmh=float(vrptw_speed),
                ),
            }
        st.session_state["vrptw_comp"] = vrptw_results
        st.session_state["vrptw_comp_df"] = df_vrptw
        st.session_state["vrptw_comp_tw"] = time_windows
        st.session_state["vrptw_comp_cap"] = vrptw_capacity

    if "vrptw_comp" in st.session_state:
        vrptw_results = st.session_state["vrptw_comp"]
        df_vrptw = st.session_state["vrptw_comp_df"]
        time_windows = st.session_state["vrptw_comp_tw"]
        cap = st.session_state["vrptw_comp_cap"]
        depot_idx = 0
        ortools_dist = vrptw_results["OR-Tools"]["total_dist"]

        # サマリーテーブル
        st.subheader("📋 結果サマリー")
        rows = []
        for algo, res in vrptw_results.items():
            dist_str = f"{res['total_dist']:.2f}" if res["total_dist"] != float("inf") else "解なし"
            gap = (
                "基準" if algo == "OR-Tools"
                else f"+{(res['total_dist'] - ortools_dist) / ortools_dist * 100:.1f}%"
                if res["total_dist"] != float("inf") and ortools_dist != float("inf")
                else "—"
            )
            rows.append({
                "アルゴリズム": algo,
                "総距離 (km)": dist_str,
                "計算時間 (秒)": f"{res['elapsed_sec']:.4f}",
                "OR-Toolsとの乖離": gap,
                "ステータス": res["status"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # 地図横並び
        st.subheader("🗺️ ルートの可視化")
        cols = st.columns(2)
        for col, (algo, res) in zip(cols, vrptw_results.items()):
            with col:
                dist_label = f"{res['total_dist']:.2f} km" if res["total_dist"] != float("inf") else "解なし"
                st.markdown(f"**{algo}**  \n総距離: {dist_label}")
                m = build_vrp_map(
                    df_vrptw, res["routes"], depot_idx,
                    arrival_times=res.get("arrival_times"),
                    time_windows=time_windows,
                )
                st_folium(m, use_container_width=True, height=420, key=f"vrptw_comp_map_{algo}")

        # 到着時刻テーブル（OR-Tools）
        if vrptw_results["OR-Tools"]["status"] != "No solution":
            st.subheader("📋 OR-Tools: 各顧客の到着時刻")
            res = vrptw_results["OR-Tools"]
            rows = []
            for v_idx, (route, arrivals) in enumerate(
                zip(res["routes"], res.get("arrival_times", []))
            ):
                if len(route) <= 2:
                    continue
                for order, (node_idx, arr) in enumerate(zip(route, arrivals)):
                    tw = time_windows[node_idx]
                    h_a, m_a = divmod(arr, 60)
                    h_s, m_s = divmod(tw[0], 60)
                    h_e, m_e = divmod(tw[1], 60)
                    rows.append({
                        "車両": f"車両{v_idx+1}",
                        "地点名": df_vrptw.iloc[node_idx]["name"],
                        "到着時刻": f"{h_a:02d}:{m_a:02d}",
                        "時間窓": f"{h_s:02d}:{m_s:02d}〜{h_e:02d}:{m_e:02d}",
                        "時間窓内": "✓" if tw[0] <= arr <= tw[1] else "✗",
                    })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)