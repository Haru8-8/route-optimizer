"""
VRPTW（Vehicle Routing Problem with Time Windows）ツール

時間窓付き・複数車両・容量制約ありのルート最適化。
OR-Tools（厳密解）と Nearest Neighbor（近似解）を比較できる。
"""

import io
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from utils.distance import build_distance_matrix
from utils.map_viz import build_vrp_map
from solver.vrptw_ortools import solve_vrptw_ortools
from solver.vrptw_nn import solve_vrptw_nn

# -----------------------------------------------
# ページ設定
# -----------------------------------------------
st.set_page_config(
    page_title="VRPTW ルート最適化",
    page_icon="⏰",
    layout="wide",
)

st.title("⏰ VRPTW ルート最適化")
st.caption("時間指定（時間窓）付きの配送ルートを自動計算します。")

# -----------------------------------------------
# サンプルデータ
# -----------------------------------------------
SAMPLE_CSV = """type,name,lat,lon,demand,time_window_start,time_window_end,service_time
depot,東京営業所,35.6812,139.7671,0,0,480,0
customer,横浜,35.4437,139.6380,15,60,180,15
customer,川崎,35.5309,139.7030,10,30,150,10
customer,さいたま,35.8617,139.6455,20,90,240,20
customer,千葉,35.6073,140.1063,12,60,210,15
customer,船橋,35.6946,139.9831,8,120,270,10
customer,松戸,35.7878,139.9026,15,90,240,15
customer,柏,35.8676,139.9756,10,150,300,10
customer,八王子,35.6664,139.3160,18,60,180,20
customer,立川,35.6982,139.4131,12,30,180,15
customer,町田,35.5404,139.4452,9,120,270,10
customer,相模原,35.5716,139.3731,14,90,240,15
"""

# -----------------------------------------------
# サイドバー
# -----------------------------------------------
st.sidebar.header("📍 地点データの入力")

if st.sidebar.button("📂 サンプルデータを使う", use_container_width=True):
    st.session_state["vrptw_csv"] = SAMPLE_CSV

st.sidebar.markdown("または")
uploaded = st.sidebar.file_uploader("CSVをアップロード", type="csv", key="vrptw_upload")
if uploaded:
    st.session_state["vrptw_csv"] = uploaded.read().decode("utf-8")

st.sidebar.markdown(
    "**時間窓は分単位**（出発時刻=0分基準）\n\n例: 60〜180 = 出発1時間後〜3時間後"
)
st.sidebar.download_button(
    label="📥 サンプルCSVをダウンロード",
    data=SAMPLE_CSV.encode("utf-8-sig"),
    file_name="vrptw_locations.csv",
    mime="text/csv",
)

st.sidebar.divider()

# -----------------------------------------------
# 車両・速度設定
# -----------------------------------------------
st.sidebar.header("🚛 車両・速度設定")
num_vehicles = st.sidebar.slider("最大使用台数", min_value=1, max_value=10, value=3)
vehicle_capacity = st.sidebar.slider("1台あたりの積載容量", min_value=10, max_value=200, value=50, step=5)
speed_kmh = st.sidebar.slider("平均速度 (km/h)", min_value=20, max_value=120, value=60, step=5)

st.sidebar.divider()

# -----------------------------------------------
# アルゴリズム設定
# -----------------------------------------------
st.sidebar.header("⚙️ アルゴリズム設定")
algo_options = ["OR-Tools", "Nearest Neighbor", "両方比較"]
selected_algo = st.sidebar.selectbox("アルゴリズムを選択", algo_options)

# -----------------------------------------------
# データ読み込み前のガイド
# -----------------------------------------------
if "vrptw_csv" not in st.session_state:
    st.info("サイドバーからCSVをアップロードするか、サンプルデータを使ってください。")
    st.subheader("CSVフォーマット")
    col1, col2 = st.columns(2)
    with col1:
        st.code(
            "type,name,lat,lon,demand,time_window_start,time_window_end,service_time\n"
            "depot,営業所,35.68,139.76,0,0,480,0\n"
            "customer,顧客A,35.44,139.63,10,60,180,15",
            language="csv"
        )
    with col2:
        st.dataframe(
            pd.DataFrame({
                "カラム名": ["type", "name", "lat", "lon", "demand",
                           "time_window_start", "time_window_end", "service_time"],
                "説明": ["depot/customer", "地点名", "緯度", "経度", "需要量",
                        "最早訪問時刻(分)", "最遅訪問時刻(分)", "滞在時間(分)"],
            }),
            hide_index=True, use_container_width=True,
        )
    st.stop()

# -----------------------------------------------
# CSV 読み込み
# -----------------------------------------------
try:
    df = pd.read_csv(io.StringIO(st.session_state["vrptw_csv"]))
    required_cols = {"type", "name", "lat", "lon", "demand",
                     "time_window_start", "time_window_end", "service_time"}
    if not required_cols.issubset(df.columns):
        st.error(f"CSVに必要なカラムがありません。必要: {required_cols}")
        st.stop()
    df = df[list(required_cols)].dropna()
    if "depot" not in df["type"].values:
        st.error("depotが1つ必要です。")
        st.stop()
except Exception as e:
    st.error(f"CSVの読み込みエラー: {e}")
    st.stop()

# データの整理
df = df[["type", "name", "lat", "lon", "demand",
         "time_window_start", "time_window_end", "service_time"]]
depot_index = df[df["type"] == "depot"].index[0]
demands = df["demand"].astype(int).tolist()
time_windows = list(zip(
    df["time_window_start"].astype(int),
    df["time_window_end"].astype(int),
))
service_times = df["service_time"].astype(int).tolist()
vehicle_capacities = [vehicle_capacity] * num_vehicles

# -----------------------------------------------
# プレビュー
# -----------------------------------------------
with st.expander("📂 読み込んだ地点データの確認", expanded=False):
    display_df = df.copy()
    display_df["時間窓"] = display_df.apply(
        lambda r: f"{int(r['time_window_start']//60):02d}:{int(r['time_window_start']%60):02d}"
                  f"〜{int(r['time_window_end']//60):02d}:{int(r['time_window_end']%60):02d}",
        axis=1
    )
    st.dataframe(
        display_df[["type", "name", "lat", "lon", "demand", "時間窓", "service_time"]],
        use_container_width=True, hide_index=True
    )

# -----------------------------------------------
# 実行ボタン
# -----------------------------------------------
run_button = st.button("🚀 最適化を実行", type="primary")

if not run_button and "vrptw_results" not in st.session_state:
    st.stop()

# -----------------------------------------------
# 最適化の実行
# -----------------------------------------------
coords = list(zip(df["lat"], df["lon"]))
dist_matrix = build_distance_matrix(coords)

if run_button:
    results = {}
    algos = (
        ["OR-Tools", "Nearest Neighbor"]
        if selected_algo == "両方比較"
        else [selected_algo]
    )
    with st.spinner("最適化中..."):
        for algo in algos:
            if algo == "OR-Tools":
                results[algo] = solve_vrptw_ortools(
                    dist_matrix, demands, vehicle_capacities,
                    time_windows, service_times,
                    int(depot_index), speed_kmh=float(speed_kmh)
                )
            else:
                results[algo] = solve_vrptw_nn(
                    dist_matrix, demands, vehicle_capacities,
                    time_windows, service_times,
                    int(depot_index), speed_kmh=float(speed_kmh)
                )
    st.session_state["vrptw_results"] = results
    st.session_state["vrptw_df"] = df
    st.session_state["vrptw_depot_index"] = int(depot_index)
    st.session_state["vrptw_time_windows"] = time_windows
    st.session_state["vrptw_vehicle_capacities"] = vehicle_capacities
    st.session_state["vrptw_selected_algo"] = selected_algo

results = st.session_state["vrptw_results"]
df = st.session_state["vrptw_df"]
depot_index = st.session_state["vrptw_depot_index"]
time_windows = st.session_state["vrptw_time_windows"]

# -----------------------------------------------
# 結果表示
# -----------------------------------------------
st.divider()

for algo, res in results.items():
    if res["status"].startswith("No solution"):
        st.error(f"**{algo}**: 解が見つかりませんでした。車両数・容量・時間窓を確認してください。")

def fmt_time(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    return f"{h:02d}:{m:02d}"

# 単一アルゴリズム表示
if st.session_state["vrptw_selected_algo"] != "両方比較":
    algo = list(results.keys())[0]
    res = results[algo]

    st.subheader(f"結果: {algo}")
    used = sum(1 for r in res['routes'] if len(r) > 2)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("総距離", f"{res['total_dist']:.2f} km")
    col2.metric("計算時間", f"{res['elapsed_sec']:.3f} 秒")
    col3.metric("使用台数 / 最大台数", f"{used} / {num_vehicles} 台")
    col4.metric("ステータス", res["status"])

    m = build_vrp_map(
        df, res["routes"], depot_index,
        arrival_times=res.get("arrival_times"),
        time_windows=time_windows,
    )
    st_folium(m, use_container_width=True, height=500)

    # 車両別テーブル（到着時刻付き）
    st.subheader("📋 車両別ルートと到着時刻")
    for v_idx, route in enumerate(res["routes"]):
        if len(route) <= 2:
            continue
        arrivals = res.get("arrival_times", [[]])[v_idx] if res.get("arrival_times") else []
        with st.expander(
            f"車両{v_idx + 1}（積載量: {res['vehicle_load'][v_idx]} / {vehicle_capacities[0]}、"
            f"距離: {res['vehicle_dist'][v_idx]:.2f} km）"
        ):
            rows = []
            for order, node_idx in enumerate(route):
                tw = time_windows[node_idx]
                arrival = fmt_time(arrivals[order]) if arrivals else "—"
                rows.append({
                    "順番": order,
                    "地点名": df.iloc[node_idx]["name"],
                    "種別": df.iloc[node_idx]["type"],
                    "到着時刻": arrival,
                    "時間窓": f"{fmt_time(tw[0])}〜{fmt_time(tw[1])}",
                })
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

# 比較表示
else:
    st.subheader("📊 アルゴリズム比較結果")

    ortools_dist = results.get("OR-Tools", {}).get("total_dist", None)
    comparison_rows = []
    for algo, res in results.items():
        gap = (
            "基準" if algo == "OR-Tools" or ortools_dist is None
            else f"+{(res['total_dist'] - ortools_dist) / ortools_dist * 100:.1f}%"
            if res["total_dist"] != float("inf") and ortools_dist != float("inf")
            else "—"
        )
        comparison_rows.append({
            "アルゴリズム": algo,
            "総距離 (km)": f"{res['total_dist']:.2f}" if res["total_dist"] != float("inf") else "解なし",
            "計算時間 (秒)": f"{res['elapsed_sec']:.3f}",
            "OR-Toolsとの乖離": gap,
            "ステータス": res["status"],
        })
    st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)

    cols = st.columns(len(results))
    for col, (algo, res) in zip(cols, results.items()):
        with col:
            st.markdown(f"**{algo}**  \n総距離: {res['total_dist']:.2f} km")
            m = build_vrp_map(
                df, res["routes"], depot_index,
                arrival_times=res.get("arrival_times"),
                time_windows=time_windows,
            )
            st_folium(m, use_container_width=True, height=420, key=f"vrptw_map_{algo}")

# -----------------------------------------------
# CSVダウンロード
# -----------------------------------------------
st.divider()
st.subheader("📥 結果のダウンロード")
for algo, res in results.items():
    rows = []
    arrivals_all = res.get("arrival_times", [])
    for v_idx, route in enumerate(res["routes"]):
        arrivals = arrivals_all[v_idx] if v_idx < len(arrivals_all) else []
        for order, node_idx in enumerate(route):
            tw = time_windows[node_idx]
            rows.append({
                "車両": v_idx + 1,
                "順番": order,
                "地点名": df.iloc[node_idx]["name"],
                "type": df.iloc[node_idx]["type"],
                "到着時刻(分)": arrivals[order] if order < len(arrivals) else "",
                "時間窓_開始(分)": tw[0],
                "時間窓_終了(分)": tw[1],
            })
    csv = pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label=f"📥 {algo} のルートをCSVでダウンロード",
        data=csv,
        file_name=f"vrptw_result_{algo}.csv",
        mime="text/csv",
        key=f"vrptw_dl_{algo}",
    )