import streamlit as st
import google.generativeai as genai
import json

# --- 1. 設定・リスクキーワード ---
RISK_KEYWORDS = {
    5: ["死にたい", "自殺", "消えたい", "殺す", "自傷", "リスカ", "終わりにしたい"],
    4: ["学校に行けない", "不登校", "いじめ", "暴力", "虐待", "親に殴られる", "限界", "眠れない"],
    3: ["辛い", "苦しい", "やめたい", "不安", "逃げたい", "独りぼっち"],
    2: ["悩んでいる", "困っている", "イライラ", "集中できない", "やる気が出ない"],
    1: []
}

def detect_risk_level(text):
    for level in range(5, 0, -1):
        if any(keyword in text for keyword in RISK_KEYWORDS.get(level, [])):
            return level
    return 1

# --- 2. UI実装 ---
st.set_page_config(page_title="安心相談チャット", page_icon="🌱")

with st.sidebar:
    st.header("⚙️ 設定")
    api_key = st.text_input("Gemini API Key", type="password")
    
    st.divider()
    st.markdown("### 🔑 APIキーの取得")
    st.markdown("[Google AI Studioで取得](https://aistudio.google.com/app/apikey)")
    
    st.divider()
    # 2026年現在の有効なモデルリスト
    model_option = st.selectbox(
        "使用モデルの選択 (2026年版)",
        ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-3-flash-preview"],
        index=0
    )

    if st.button("会話履歴をリセット"):
        st.session_state.messages = []
        st.rerun()

st.title("🌱 安心相談チャット")
st.caption("最新のGeminiエンジンを搭載した相談支援システム")

if not api_key:
    st.warning("サイドバーにAPIキーを入力してください。")
    st.stop()

# APIの初期化
genai.configure(api_key=api_key)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 3. メインロジック ---
if prompt := st.chat_input("今、どんなことを考えていますか？"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    risk_level = detect_risk_level(prompt)

    system_instruction = f"""
    あなたは温かいプロのスクールカウンセラーです。
    必ず以下のJSON形式のみで回答してください。
    {{
        "needs": "傾聴 または 改善策 または 共考",
        "reply": "相談者への返答"
    }}
    現在のリスクレベル: {risk_level}
    """

    try:
        model = genai.GenerativeModel(
            model_name=model_option,
            system_instruction=system_instruction
        )

        with st.chat_message("assistant"):
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            res_data = json.loads(response.text)
            reply_text = res_data.get("reply", "...")
            st.markdown(reply_text)
            
            if risk_level >= 4:
                st.error("⚠️ 一人で抱え込まずに、相談してみませんか？")
                st.info("24時間子供SOSダイヤル: 0120-0-78310")

            st.session_state.messages.append({"role": "assistant", "content": reply_text})

    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            st.error(f"モデル '{model_option}' は現在お使いの環境で利用できません。")
        elif "429" in error_msg:
            st.error("利用制限（クォータ）を超えました。1分ほど待ってから再試行してください。")
        else:
            st.error(f"エラーが発生しました: {error_msg}")