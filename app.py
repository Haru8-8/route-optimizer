"""
ルート最適化ツール - トップページ

TSP・VRP・VRPTWの3種類のルート最適化ツールへの
ランディングページ。
"""

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="ルート最適化ツール",
    page_icon="🚀",
    layout="wide",
)

st.title("🚀 ルート最適化ツール")
st.caption("TSP・VRP・VRPTWの3種類のルート最適化アルゴリズムをインタラクティブに試せます。")

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🗺️ TSP")
    st.markdown("**巡回セールスマン問題**")
    st.markdown(
        "1台の車両が全地点を1回ずつ巡回する最短ルートを求めます。"
        "営業の訪問ルートや観光地の巡回計画に活用できます。"
    )
    st.markdown("**対応アルゴリズム**")
    st.markdown("- OR-Tools（厳密解）\n- 貪欲法 + 2-opt\n- 焼きなまし法（SA）")
    st.page_link("pages/tsp.py", label="TSPツールを使う →", icon="🗺️")

with col2:
    st.subheader("🚛 VRP")
    st.markdown("**車両ルーティング問題**")
    st.markdown(
        "複数の車両が容量制約を守りながら顧客を効率よく巡回します。"
        "配送業務や営業チームの担当エリア分けに活用できます。"
    )
    st.markdown("**対応アルゴリズム**")
    st.markdown("- OR-Tools（厳密解）\n- Clarke-Wright節約法")
    st.page_link("pages/vrp.py", label="VRPツールを使う →", icon="🚛")

with col3:
    st.subheader("⏰ VRPTW")
    st.markdown("**時間窓付き車両ルーティング問題**")
    st.markdown(
        "VRPに加えて各顧客への訪問時間帯の指定に対応します。"
        "「午前中に届けてほしい」などの時間指定がある配送に活用できます。"
    )
    st.markdown("**対応アルゴリズム**")
    st.markdown("- OR-Tools（厳密解）\n- Nearest Neighbor（時間窓考慮版）")
    st.page_link("pages/vrptw.py", label="VRPTWツールを使う →", icon="⏰")

st.divider()

st.subheader("📋 どのツールを使えばいい？")
guide_df = pd.DataFrame({
    "条件": [
        "車両は1台でいい",
        "車両が複数台ある",
        "各車両に積載量の上限がある",
        "顧客ごとに訪問できる時間帯がある",
    ],
    "使うべきツール": ["TSP", "VRP / VRPTW", "VRP / VRPTW", "VRPTW"],
    "備考": [
        "最もシンプルな設定",
        "VRPから始めて必要に応じてVRPTWへ",
        "demandとcapacityで設定",
        "time_window_start/endで設定（分単位）",
    ],
})
st.dataframe(guide_df, use_container_width=True, hide_index=True)

st.divider()

st.subheader("🔗 リンク")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**GitHub**\nhttps://github.com/Haru8-8/route-optimizer")
with col2:
    st.markdown("**Qiita記事**\nhttps://qiita.com/Haru8-8/items/34b4fd4d1c726ab11d7d")