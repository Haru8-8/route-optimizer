"""
VRP（Vehicle Routing Problem）ツール

複数車両・容量制約ありのルート最適化。
OR-Tools（厳密解）と Clarke-Wright節約法（近似解）を比較できる。
"""

import io
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from utils.distance import build_distance_matrix
from utils.map_viz import build_vrp_map
from solver.vrp_ortools import solve_vrp_ortools
from solver.vrp_clarke_wright import solve_vrp_clarke_wright

# -----------------------------------------------
# ページ設定
# -----------------------------------------------
st.set_page_config(
    page_title="VRP ルート最適化",
    page_icon="🚛",
    layout="wide",
)

st.title("🚛 VRP ルート最適化")
st.caption("複数車両で顧客を効率よく巡回する配送ルートを自動計算します。")

# -----------------------------------------------
# サンプルデータ
# -----------------------------------------------
SAMPLE_CSV = """type,name,lat,lon,demand
depot,東京営業所,35.6812,139.7671,0
customer,横浜,35.4437,139.6380,15
customer,川崎,35.5309,139.7030,10
customer,さいたま,35.8617,139.6455,20
customer,千葉,35.6073,140.1063,12
customer,船橋,35.6946,139.9831,8
customer,松戸,35.7878,139.9026,15
customer,柏,35.8676,139.9756,10
customer,八王子,35.6664,139.3160,18
customer,立川,35.6982,139.4131,12
customer,町田,35.5404,139.4452,9
customer,相模原,35.5716,139.3731,14
"""

# -----------------------------------------------
# サイドバー
# -----------------------------------------------
st.sidebar.header("📍 地点データの入力")

if st.sidebar.button("📂 サンプルデータを使う", use_container_width=True):
    st.session_state["vrp_csv"] = SAMPLE_CSV

st.sidebar.markdown("または")
uploaded = st.sidebar.file_uploader("CSVをアップロード", type="csv", key="vrp_upload")
if uploaded:
    st.session_state["vrp_csv"] = uploaded.read().decode("utf-8")

st.sidebar.markdown(
    "**CSVフォーマット**\n```\ntype,name,lat,lon,demand\ndepot,営業所,35.68,139.76,0\ncustomer,顧客A,35.44,139.63,10\n```"
)
st.sidebar.download_button(
    label="📥 サンプルCSVをダウンロード",
    data=SAMPLE_CSV.encode("utf-8-sig"),
    file_name="vrp_locations.csv",
    mime="text/csv",
)

st.sidebar.divider()

# -----------------------------------------------
# 車両設定
# -----------------------------------------------
st.sidebar.header("🚛 車両設定")
num_vehicles = st.sidebar.slider("最大使用台数", min_value=1, max_value=10, value=3)
vehicle_capacity = st.sidebar.slider("1台あたりの積載容量", min_value=10, max_value=200, value=50, step=5)

st.sidebar.divider()

# -----------------------------------------------
# アルゴリズム設定
# -----------------------------------------------
st.sidebar.header("⚙️ アルゴリズム設定")
algo_options = ["OR-Tools", "Clarke-Wright節約法", "両方比較"]
selected_algo = st.sidebar.selectbox("アルゴリズムを選択", algo_options)

# -----------------------------------------------
# データ読み込み前のガイド
# -----------------------------------------------
if "vrp_csv" not in st.session_state:
    st.info("サイドバーからCSVをアップロードするか、サンプルデータを使ってください。")
    st.subheader("CSVフォーマット")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**入力形式**")
        st.code("type,name,lat,lon,demand\ndepot,営業所,35.6812,139.7671,0\ncustomer,顧客A,35.4437,139.6380,15", language="csv")
    with col2:
        st.markdown("**カラム説明**")
        st.dataframe(
            pd.DataFrame({
                "カラム名": ["type", "name", "lat", "lon", "demand"],
                "説明": ["depot または customer", "地点名", "緯度", "経度", "需要量（depotは0）"],
            }),
            hide_index=True, use_container_width=True,
        )
    st.stop()

# -----------------------------------------------
# CSV 読み込み
# -----------------------------------------------
try:
    df = pd.read_csv(io.StringIO(st.session_state["vrp_csv"]))
    required_cols = {"type", "name", "lat", "lon", "demand"}
    if not required_cols.issubset(df.columns):
        st.error(f"CSVに必要なカラムがありません。必要: {required_cols}")
        st.stop()
    df = df[["type", "name", "lat", "lon", "demand"]].dropna()
    if "depot" not in df["type"].values:
        st.error("depotが1つ必要です。")
        st.stop()
except Exception as e:
    st.error(f"CSVの読み込みエラー: {e}")
    st.stop()

depot_index = df[df["type"] == "depot"].index[0]
demands = df["demand"].astype(int).tolist()
vehicle_capacities = [vehicle_capacity] * num_vehicles

# -----------------------------------------------
# プレビュー
# -----------------------------------------------
with st.expander("📂 読み込んだ地点データの確認", expanded=False):
    st.dataframe(df, use_container_width=True, hide_index=True)
    total_demand = sum(d for d in demands if d > 0)
    st.caption(f"顧客数: {len(df) - 1} / 総需要量: {total_demand} / 車両あたり容量: {vehicle_capacity} × {num_vehicles}台 = {vehicle_capacity * num_vehicles}")
    if total_demand > vehicle_capacity * num_vehicles:
        st.warning("⚠️ 総需要量が全車両の容量合計を超えています。車両数または容量を増やしてください。")

# -----------------------------------------------
# 実行ボタン
# -----------------------------------------------
run_button = st.button("🚀 最適化を実行", type="primary")

if not run_button and "vrp_results" not in st.session_state:
    st.stop()

# -----------------------------------------------
# 最適化の実行
# -----------------------------------------------
coords = list(zip(df["lat"], df["lon"]))
dist_matrix = build_distance_matrix(coords)

if run_button:
    results = {}
    algos = (
        ["OR-Tools", "Clarke-Wright節約法"]
        if selected_algo == "両方比較"
        else [selected_algo]
    )
    with st.spinner("最適化中..."):
        for algo in algos:
            if algo == "OR-Tools":
                results[algo] = solve_vrp_ortools(
                    dist_matrix, demands, vehicle_capacities, int(depot_index)
                )
            else:
                results[algo] = solve_vrp_clarke_wright(
                    dist_matrix, demands, vehicle_capacities, int(depot_index)
                )
    st.session_state["vrp_results"] = results
    st.session_state["vrp_df"] = df
    st.session_state["vrp_dist_matrix"] = dist_matrix
    st.session_state["vrp_demands"] = demands
    st.session_state["vrp_vehicle_capacities"] = vehicle_capacities
    st.session_state["vrp_depot_index"] = int(depot_index)
    st.session_state["vrp_selected_algo"] = selected_algo

results = st.session_state["vrp_results"]
df = st.session_state["vrp_df"]
depot_index = st.session_state["vrp_depot_index"]

# -----------------------------------------------
# 結果表示
# -----------------------------------------------
st.divider()

# 解なしの場合
for algo, res in results.items():
    if res["status"] == "No solution":
        st.error(f"**{algo}**: 解が見つかりませんでした。最大使用台数または積載容量を増やしてください。")

# 単一アルゴリズム表示
if st.session_state["vrp_selected_algo"] != "両方比較":
    algo = list(results.keys())[0]
    res = results[algo]

    if res["status"] == "No solution":
        st.stop()

    st.subheader(f"結果: {algo}")
    used = sum(1 for r in res['routes'] if len(r) > 2)
    col1, col2, col3 = st.columns(3)
    col1.metric("総距離", f"{res['total_dist']:.2f} km")
    col2.metric("計算時間", f"{res['elapsed_sec']:.3f} 秒")
    col3.metric("使用台数 / 最大台数", f"{used} / {num_vehicles} 台")

    if used > num_vehicles:
        st.warning(f"⚠️ 最大使用台数（{num_vehicles}台）を超えて{used}台が必要です。最大使用台数または積載容量を増やしてください。")

    m = build_vrp_map(df, res["routes"], depot_index)
    st_folium(m, use_container_width=True, height=500)

    # 車両別テーブル
    st.subheader("📋 車両別ルート")
    for v_idx, route in enumerate(res["routes"]):
        if len(route) <= 2:
            continue
        with st.expander(f"車両{v_idx + 1}（積載量: {res['vehicle_load'][v_idx]} / {st.session_state['vrp_vehicle_capacities'][0]}、距離: {res['vehicle_dist'][v_idx]:.2f} km）"):
            route_names = [df.iloc[idx]["name"] for idx in route]
            st.write(" → ".join(route_names))

# 比較表示
else:
    st.subheader("📊 アルゴリズム比較結果")

    ortools_dist = results.get("OR-Tools", {}).get("total_dist", None)
    comparison_rows = []
    for algo, res in results.items():
        used = sum(1 for r in res['routes'] if len(r) > 2)
        gap = (
            "基準" if algo == "OR-Tools" or ortools_dist is None
            else f"+{(res['total_dist'] - ortools_dist) / ortools_dist * 100:.1f}%"
            if res["total_dist"] != float("inf") else "—"
        )
        comparison_rows.append({
            "アルゴリズム": algo,
            "総距離 (km)": f"{res['total_dist']:.2f}" if res["total_dist"] != float("inf") else "解なし",
            "使用台数 / 最大台数": f"{used} / {num_vehicles} 台" if res["status"] != "No solution" else "—",
            "計算時間 (秒)": f"{res['elapsed_sec']:.3f}",
            "OR-Toolsとの乖離": gap,
            "ステータス": res["status"],
        })
    st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)

    # 台数超過の警告
    for algo, res in results.items():
        used = sum(1 for r in res['routes'] if len(r) > 2)
        if res["status"] != "No solution" and used > num_vehicles:
            st.warning(f"⚠️ {algo}: 最大使用台数（{num_vehicles}台）を超えて{used}台が必要です。")

    cols = st.columns(len(results))
    for col, (algo, res) in zip(cols, results.items()):
        with col:
            st.markdown(f"**{algo}**  \n総距離: {res['total_dist']:.2f} km")
            m = build_vrp_map(df, res["routes"], depot_index)
            st_folium(m, use_container_width=True, height=420, key=f"vrp_map_{algo}")

# -----------------------------------------------
# CSVダウンロード
# -----------------------------------------------
st.divider()
st.subheader("📥 結果のダウンロード")
for algo, res in results.items():
    rows = []
    for v_idx, route in enumerate(res["routes"]):
        for order, node_idx in enumerate(route):
            rows.append({
                "車両": v_idx + 1,
                "順番": order,
                "地点名": df.iloc[node_idx]["name"],
                "type": df.iloc[node_idx]["type"],
                "緯度": df.iloc[node_idx]["lat"],
                "経度": df.iloc[node_idx]["lon"],
                "需要量": df.iloc[node_idx]["demand"],
            })
    csv = pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label=f"📥 {algo} のルートをCSVでダウンロード",
        data=csv,
        file_name=f"vrp_result_{algo}.csv",
        mime="text/csv",
        key=f"vrp_dl_{algo}",
    )