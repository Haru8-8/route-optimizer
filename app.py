"""
TSP ルート最適化ツール（Streamlit UI）

使い方:
    pip install -r requirements.txt
    streamlit run app.py

【VRP拡張時の移行メモ】
VRPを追加するタイミングで以下の対応を行う:
1. このファイルを pages/tsp.py に移動
2. app.py を新規作成してトップページ（ツール選択画面）にする
3. pages/vrp.py を新規作成してVRPツールを実装
4. pages/comparison.py はTSP/VRP両対応に拡張
"""

import io
import time
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from utils.distance import build_distance_matrix, total_distance
from utils.map_viz import build_route_map
from solver.tsp_ortools import solve_tsp_ortools
from solver.tsp_greedy2opt import solve_tsp_greedy2opt
from solver.tsp_sa import solve_tsp_sa

# -----------------------------------------------
# ページ設定
# -----------------------------------------------
st.set_page_config(
    page_title="TSPルート最適化ツール",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ TSPルート最適化ツール")
st.caption("CSVで地点を入力し、最短巡回ルートを自動計算します。")

# -----------------------------------------------
# サンプルデータ
# -----------------------------------------------
SAMPLE_CSV = """name,lat,lon
東京,35.6812,139.7671
横浜,35.4437,139.6380
さいたま,35.8617,139.6455
千葉,35.6073,140.1063
宇都宮,36.5657,139.8836
前橋,36.3898,139.0634
水戸,36.3418,140.4468
甲府,35.6642,138.5681
長野,36.6513,138.1810
新潟,37.9162,139.0364
静岡,34.9769,138.3831
名古屋,35.1815,136.9066
"""

# -----------------------------------------------
# サイドバー
# -----------------------------------------------
st.sidebar.header("📍 地点データの入力")

# サンプルデータボタン
if st.sidebar.button("📂 サンプルデータを使う", use_container_width=True):
    st.session_state["csv_text"] = SAMPLE_CSV

st.sidebar.markdown("または")

uploaded_file = st.sidebar.file_uploader("CSVをアップロード", type="csv")
if uploaded_file:
    st.session_state["csv_text"] = uploaded_file.read().decode("utf-8")

st.sidebar.markdown(
    "**CSVフォーマット**\n```\nname,lat,lon\n東京,35.6812,139.7671\n```"
)

# サンプルCSVダウンロード
st.sidebar.download_button(
    label="📥 サンプルCSVをダウンロード",
    data=SAMPLE_CSV.encode("utf-8-sig"),
    file_name="locations.csv",
    mime="text/csv",
)

st.sidebar.divider()

# -----------------------------------------------
# アルゴリズム設定
# -----------------------------------------------
st.sidebar.header("⚙️ アルゴリズム設定")

algo_options = ["OR-Tools", "貪欲法+2-opt", "SA", "すべて比較"]
selected_algo = st.sidebar.selectbox("アルゴリズムを選択", algo_options)

# SAパラメータ（折りたたみ）
with st.sidebar.expander("🔧 SA パラメータ（上級者向け）"):
    initial_temp = st.slider("初期温度", 100.0, 5000.0, 1000.0, step=100.0)
    cooling_rate = st.slider("冷却率", 0.900, 0.999, 0.995, step=0.001, format="%.3f")

# -----------------------------------------------
# データ読み込み前のガイド
# -----------------------------------------------
if "csv_text" not in st.session_state:
    st.info("サイドバーからCSVをアップロードするか、サンプルデータを使ってください。")
    st.subheader("CSVフォーマット")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**入力形式**")
        st.code("name,lat,lon\n東京,35.6812,139.7671\n横浜,35.4437,139.6380\n...", language="csv")
    with col2:
        st.markdown("**カラム説明**")
        st.dataframe(
            pd.DataFrame({
                "カラム名": ["name", "lat", "lon"],
                "説明": ["地点名（任意の文字列）", "緯度（10進数）", "経度（10進数）"],
                "例": ["東京", "35.6812", "139.7671"],
            }),
            hide_index=True,
            use_container_width=True,
        )
    st.stop()

# -----------------------------------------------
# CSV 読み込み
# -----------------------------------------------
try:
    df = pd.read_csv(io.StringIO(st.session_state["csv_text"]))
    required_cols = {"name", "lat", "lon"}
    if not required_cols.issubset(df.columns):
        st.error(f"CSVに必要なカラムがありません。必要: {required_cols}")
        st.stop()
    df = df[["name", "lat", "lon"]].dropna()
    if len(df) < 3:
        st.error("地点は3つ以上必要です。")
        st.stop()
except Exception as e:
    st.error(f"CSVの読み込みエラー: {e}")
    st.stop()

# -----------------------------------------------
# 出発地点の選択
# -----------------------------------------------
st.sidebar.divider()
st.sidebar.header("🚩 出発地点")
start_name = st.sidebar.selectbox("出発地点を選択", df["name"].tolist())
start_index = df[df["name"] == start_name].index[0]

# -----------------------------------------------
# 地点プレビュー
# -----------------------------------------------
with st.expander("📂 読み込んだ地点データの確認", expanded=False):
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"合計 {len(df)} 地点")

# -----------------------------------------------
# 実行ボタン
# -----------------------------------------------
col1, col2 = st.columns([1, 3])
with col1:
    run_button = st.button("🚀 最適化を実行", type="primary", use_container_width=True)

if not run_button and "results" not in st.session_state:
    st.stop()

# -----------------------------------------------
# 最適化の実行
# -----------------------------------------------
coords = list(zip(df["lat"], df["lon"]))
dist_matrix = build_distance_matrix(coords)

if run_button:
    results = {}
    algos_to_run = (
        ["OR-Tools", "貪欲法+2-opt", "SA"]
        if selected_algo == "すべて比較"
        else [selected_algo]
    )

    with st.spinner("最適化中..."):
        for algo in algos_to_run:
            if algo == "OR-Tools":
                results[algo] = solve_tsp_ortools(dist_matrix, start_index)
            elif algo == "貪欲法+2-opt":
                results[algo] = solve_tsp_greedy2opt(dist_matrix, start_index)
            elif algo == "SA":
                results[algo] = solve_tsp_sa(
                    dist_matrix, start_index,
                    initial_temp=initial_temp,
                    cooling_rate=cooling_rate,
                )

    st.session_state["results"] = results
    st.session_state["selected_algo"] = selected_algo
    st.session_state["df"] = df
    st.session_state["dist_matrix"] = dist_matrix

results = st.session_state["results"]
df = st.session_state["df"]

# -----------------------------------------------
# 結果表示（単一アルゴリズム）
# -----------------------------------------------
if st.session_state["selected_algo"] != "すべて比較":
    algo = list(results.keys())[0]
    res = results[algo]

    st.divider()
    st.subheader(f"結果: {algo}")

    # サマリー metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("総距離", f"{res['total_dist']:.2f} km")
    col2.metric("計算時間", f"{res['elapsed_sec']:.3f} 秒")
    col3.metric("地点数", f"{len(df)} 地点")

    # 地図
    m = build_route_map(df, res["route"], algo)
    st_folium(m, use_container_width=True, height=500)

    # ルート順テーブル
    st.subheader("📋 ルート順")
    route_rows = []
    route = res["route"]
    for order, idx in enumerate(route):
        next_idx = route[(order + 1) % len(route)]
        seg_dist = st.session_state["dist_matrix"][idx][next_idx]
        route_rows.append({
            "順番": order + 1 if order > 0 else "🚩 出発",
            "地点名": df.iloc[idx]["name"],
            "次の地点まで (km)": f"{seg_dist:.2f}",
        })
    # 最後に出発地点へ戻る行を追加
    route_rows[-1]["次の地点まで (km)"] = f"{st.session_state['dist_matrix'][route[-1]][route[0]]:.2f} (出発地点へ戻る)"

    st.dataframe(
        pd.DataFrame(route_rows),
        use_container_width=True,
        hide_index=True,
    )

# -----------------------------------------------
# 結果表示（すべて比較）
# -----------------------------------------------
else:
    st.divider()
    st.subheader("📊 アルゴリズム比較結果")

    # 比較テーブル
    ortools_dist = results.get("OR-Tools", {}).get("total_dist", None)
    comparison_rows = []
    for algo, res in results.items():
        gap = (
            f"{(res['total_dist'] - ortools_dist) / ortools_dist * 100:.1f}%"
            if ortools_dist and algo != "OR-Tools"
            else "基準"
        )
        comparison_rows.append({
            "アルゴリズム": algo,
            "総距離 (km)": f"{res['total_dist']:.2f}",
            "計算時間 (秒)": f"{res['elapsed_sec']:.3f}",
            "OR-Toolsとの乖離": gap,
        })
    st.dataframe(
        pd.DataFrame(comparison_rows),
        use_container_width=True,
        hide_index=True,
    )

    # 地図を横並び表示
    algo_list = list(results.keys())
    cols = st.columns(len(algo_list))
    for col, algo in zip(cols, algo_list):
        with col:
            st.markdown(f"**{algo}**  \n総距離: {results[algo]['total_dist']:.2f} km")
            m = build_route_map(df, results[algo]["route"], algo)
            st_folium(m, use_container_width=True, height=400, key=f"map_{algo}")

    # ルート順テーブル（タブ形式）
    st.subheader("📋 ルート順")
    tabs = st.tabs(algo_list)
    for tab, algo in zip(tabs, algo_list):
        with tab:
            route = results[algo]["route"]
            route_rows = []
            for order, idx in enumerate(route):
                next_idx = route[(order + 1) % len(route)]
                seg_dist = st.session_state["dist_matrix"][idx][next_idx]
                route_rows.append({
                    "順番": order + 1 if order > 0 else "🚩 出発",
                    "地点名": df.iloc[idx]["name"],
                    "次の地点まで (km)": f"{seg_dist:.2f}",
                })
            st.dataframe(
                pd.DataFrame(route_rows),
                use_container_width=True,
                hide_index=True,
            )

# -----------------------------------------------
# CSVダウンロード
# -----------------------------------------------
st.divider()
st.subheader("📥 結果のダウンロード")

for algo, res in results.items():
    route = res["route"]
    download_rows = []
    for order, idx in enumerate(route):
        next_idx = route[(order + 1) % len(route)]
        download_rows.append({
            "順番": order + 1,
            "地点名": df.iloc[idx]["name"],
            "緯度": df.iloc[idx]["lat"],
            "経度": df.iloc[idx]["lon"],
            "次の地点まで_km": round(st.session_state["dist_matrix"][idx][next_idx], 3),
        })
    result_csv = pd.DataFrame(download_rows).to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label=f"📥 {algo} のルートをCSVでダウンロード",
        data=result_csv,
        file_name=f"route_{algo}.csv",
        mime="text/csv",
        key=f"dl_{algo}",
    )