"""
アルゴリズム比較ページ（TSP）

ランダム生成した地点でOR-Tools・貪欲法+2-opt・SAを比較する。

【VRP拡張時の移行メモ】
- このファイルを pages/tsp_comparison.py にリネーム
- pages/vrp_comparison.py を新規作成してVRP比較ページを実装
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

    # -----------------------------------------------
    # Mac環境: ヒラギノフォントを使用
    # -----------------------------------------------
    if platform.system() == "Darwin":
        for font_name in ["Hiragino Sans", "Hiragino Maru Gothic Pro", "AppleGothic"]:
            if any(font_name in f.name for f in font_manager.fontManager.ttflist):
                mpl.rcParams['font.family'] = font_name
                return
        # フォントリストに見つからない場合はファイルパスで直接探す
        mac_patterns = [
            '/System/Library/Fonts/**/Hiragino*.ttc',
            '/Library/Fonts/**/Hiragino*.ttc',
        ]
        for pattern in mac_patterns:
            files = glob.glob(pattern, recursive=True)
            if files:
                font_manager.fontManager.addfont(files[0])
                prop = font_manager.FontProperties(fname=files[0])
                mpl.rcParams['font.family'] = prop.get_name()
                return

    # -----------------------------------------------
    # Linux環境（Streamlit Cloud）: Noto CJKを使用
    # -----------------------------------------------
    font_manager._load_fontmanager(try_read_cache=False)
    for font in font_manager.fontManager.ttflist:
        if 'Noto' in font.name and 'CJK' in font.name:
            mpl.rcParams['font.family'] = font.name
            return

    # Noto CJK が見つからない場合はファイルパスで直接探す
    linux_patterns = [
        '/usr/share/fonts/**/Noto*CJK*.ttc',
        '/usr/share/fonts/**/Noto*CJK*.otf',
        '/usr/share/fonts/**/*noto*cjk*.ttc',
    ]
    for pattern in linux_patterns:
        files = glob.glob(pattern, recursive=True)
        if files:
            font_manager.fontManager.addfont(files[0])
            prop = font_manager.FontProperties(fname=files[0])
            mpl.rcParams['font.family'] = prop.get_name()
            return

_setup_japanese_font()

from utils.distance import build_distance_matrix
from utils.map_viz import build_comparison_map
from solver.tsp_ortools import solve_tsp_ortools
from solver.tsp_greedy2opt import solve_tsp_greedy2opt
from solver.tsp_sa import solve_tsp_sa

# -----------------------------------------------
# ページ設定
# -----------------------------------------------
st.set_page_config(
    page_title="アルゴリズム比較",
    page_icon="📊",
    layout="wide",
)

st.title("📊 アルゴリズム比較")
st.caption("ランダム生成した地点でOR-Tools・貪欲法+2-opt・SAの性能を比較します。")

# -----------------------------------------------
# パラメータ設定（サイドバー）
# -----------------------------------------------
st.sidebar.header("⚙️ 比較パラメータ")

n_points = st.sidebar.slider("地点数", min_value=5, max_value=50, value=15, step=1)
random_seed = st.sidebar.number_input("乱数シード", min_value=0, max_value=9999, value=42)

st.sidebar.divider()
st.sidebar.subheader("🔧 SA パラメータ")
initial_temp = st.sidebar.slider("初期温度", 100.0, 5000.0, 1000.0, step=100.0)
cooling_rate = st.sidebar.slider("冷却率", 0.900, 0.999, 0.995, step=0.001, format="%.3f")

st.sidebar.divider()
run_button = st.sidebar.button("🚀 比較を実行", type="primary", use_container_width=True)

# -----------------------------------------------
# ランダム地点の生成（日本国内に限定）
# -----------------------------------------------
def generate_random_locations(n: int, seed: int) -> pd.DataFrame:
    """
    日本国内にランダムな地点を生成する

    緯度: 31.0 〜 44.0
    経度: 130.0 〜 145.0
    """
    rng = np.random.default_rng(seed)
    lats = rng.uniform(31.0, 44.0, n)
    lons = rng.uniform(130.0, 145.0, n)
    names = [f"地点{i+1:02d}" for i in range(n)]
    return pd.DataFrame({"name": names, "lat": lats, "lon": lons})


# -----------------------------------------------
# 実行前のガイド
# -----------------------------------------------
if not run_button and "comp_results" not in st.session_state:
    st.info("サイドバーでパラメータを設定し、「比較を実行」ボタンを押してください。")

    st.subheader("比較するアルゴリズム")
    algo_df = pd.DataFrame({
        "アルゴリズム": ["OR-Tools", "貪欲法+2-opt", "SA（焼きなまし法）"],
        "種別": ["厳密解法", "ヒューリスティック", "メタヒューリスティック"],
        "特徴": [
            "最適解（または制限時間内の最良解）を保証",
            "最近傍法で初期解を作り、2-optで局所最適化",
            "確率的に悪化を許容しながら大域的最適解を探索",
        ],
    })
    st.dataframe(algo_df, use_container_width=True, hide_index=True)
    st.stop()

# -----------------------------------------------
# 比較の実行
# -----------------------------------------------
if run_button:
    df = generate_random_locations(n_points, random_seed)
    coords = list(zip(df["lat"], df["lon"]))
    dist_matrix = build_distance_matrix(coords)

    comp_results = {}
    with st.spinner("3アルゴリズムを計算中..."):
        comp_results["OR-Tools"] = solve_tsp_ortools(dist_matrix, start_index=0)
        comp_results["貪欲法+2-opt"] = solve_tsp_greedy2opt(dist_matrix, start_index=0)
        comp_results["SA"] = solve_tsp_sa(
            dist_matrix, start_index=0,
            initial_temp=initial_temp,
            cooling_rate=cooling_rate,
        )

    st.session_state["comp_results"] = comp_results
    st.session_state["comp_df"] = df
    st.session_state["comp_dist_matrix"] = dist_matrix
    st.session_state["comp_n_points"] = n_points

comp_results = st.session_state["comp_results"]
df = st.session_state["comp_df"]
dist_matrix = st.session_state["comp_dist_matrix"]

# -----------------------------------------------
# 比較テーブル
# -----------------------------------------------
st.divider()
st.subheader("📋 結果サマリー")

ortools_dist = comp_results["OR-Tools"]["total_dist"]
summary_rows = []
for algo, res in comp_results.items():
    gap = (
        "基準"
        if algo == "OR-Tools"
        else f"+{(res['total_dist'] - ortools_dist) / ortools_dist * 100:.1f}%"
    )
    summary_rows.append({
        "アルゴリズム": algo,
        "総距離 (km)": f"{res['total_dist']:.2f}",
        "計算時間 (秒)": f"{res['elapsed_sec']:.4f}",
        "OR-Toolsとの乖離": gap,
        "ステータス": res["status"],
    })

st.dataframe(
    pd.DataFrame(summary_rows),
    use_container_width=True,
    hide_index=True,
)

# -----------------------------------------------
# 地図3枚横並び
# -----------------------------------------------
st.subheader("🗺️ ルートの可視化")

col1, col2, col3 = st.columns(3)
for col, (algo, res) in zip([col1, col2, col3], comp_results.items()):
    with col:
        st.markdown(f"**{algo}**")
        m = build_comparison_map(df, res["route"], algo, res["total_dist"])
        st_folium(m, use_container_width=True, height=380, key=f"comp_map_{algo}")

# -----------------------------------------------
# SAの収束グラフ
# -----------------------------------------------
st.subheader("📈 SAの収束グラフ")
st.caption("焼きなまし法のイテレーションごとの最良距離の推移です。")

sa_history = comp_results["SA"].get("history", [])

if sa_history:
    fig, ax = plt.subplots(figsize=(10, 4))

    ax.plot(sa_history, color="#FF5722", linewidth=1.5, label="SA 最良距離")
    ax.axhline(
        y=ortools_dist,
        color="#2196F3",
        linestyle="--",
        linewidth=1.5,
        label=f"OR-Tools ({ortools_dist:.2f} km)",
    )
    greedy_dist = comp_results["貪欲法+2-opt"]["total_dist"]
    ax.axhline(
        y=greedy_dist,
        color="#4CAF50",
        linestyle="--",
        linewidth=1.5,
        label=f"Greedy+2-opt ({greedy_dist:.2f} km)",
    )

    ax.set_xlabel("Temperature Step")
    ax.set_ylabel("Distance (km)")
    ax.set_title("SA Convergence")
    ax.legend()
    ax.grid(True, alpha=0.3)

    st.pyplot(fig)
    plt.close(fig)

# -----------------------------------------------
# 地点データの表示
# -----------------------------------------------
with st.expander("📂 使用した地点データ", expanded=False):
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"乱数シード: {st.session_state.get('comp_n_points', '')} 地点 / seed={random_seed}")