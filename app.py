import streamlit as st
import google.generativeai as genai
import json

# --- 1. カウンセリング・リスク定義 ---
RISK_KEYWORDS = {
    5: ["死にたい", "自殺", "消えたい", "殺す", "自傷", "リスカ", "おわりにする"],
    4: ["学校に行けない", "不登校", "いじめ", "暴力", "虐待", "殴られる", "限界", "眠れない"],
    3: ["辛い", "苦しい", "やめたい", "不安", "逃げたい", "孤独", "独りぼっち"],
    2: ["悩んでいる", "困っている", "イライラ", "集中できない", "やる気が出ない"],
    1: []
}

def detect_risk_level(text):
    for level in range(5, 0, -1):
        if any(keyword in text for keyword in RISK_KEYWORDS.get(level, [])):
            return level
    return 1

# --- 2. UI設計（モバイル最適化） ---
st.set_page_config(page_title="心の相談室", page_icon="🤝", layout="centered")

# CSSの修正（unsafe_allow_html=True に修正済み）
st.markdown("""
    <style>
    .stApp { max-width: 800px; margin: 0 auto; }
    .stButton>button { width: 100%; border-radius: 20px; height: 3em; margin-top: 10px; }
    .stChatMessage { border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤝 心の相談室")

# 上部の設定メニュー
with st.expander("⚙️ 初期設定・使い方", expanded=False):
    st.markdown("### APIキーの設定")
    api_key = st.text_input("Gemini API Key", type="password")
    st.markdown("[👉 APIキーを取得する（Google AI Studio）](https://aistudio.google.com/app/apikey)")
    
    st.divider()
    if st.button("会話をリセットして最初から話す"):
        st.session_state.clear()
        st.rerun()

# APIキーチェック
if not api_key:
    st.info("上の「初期設定」メニューを開き、APIキーを入力してください。")
    st.stop()

# モデル設定
genai.configure(api_key=api_key)
MODEL_ID = "gemini-2.5-flash"

if "messages" not in st.session_state:
    st.session_state.messages = []

# チャット履歴の表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 3. メインロジック ---

if prompt := st.chat_input("今、どんなお気持ちですか？"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    risk_level = detect_risk_level(prompt)

    # プロフェッショナル・カウンセラー・プロンプト
    system_instruction = f"""
    あなたは、経験豊富なスクールカウンセラーです。
    来談者中心療法とマイクロカウンセリングの技法を使い、相談者が安心して話せる場を作ってください。

    【カウンセリング指針】
    1. 感情の反射：相談者の言葉の奥にある感情を汲み取り、言語化を助けます。
    2. 評価しない姿勢：良い・悪いという判断をせず、ありのままを受け止めます。
    3. 相談者のペースを尊重：急いで解決策を出さず、まずは十分に聴くことを優先します。

    【リスクレベル: {risk_level}】
    - レベル4以上の場合は、受容しつつ、安全確保のために専門機関（保健室や相談窓口）への連絡を促してください。

    【出力形式：必ずJSONのみ】
    {{
        "analysis": "心理状態の分析",
        "reply": "カウンセラーとしての返答"
    }}
    """

    try:
        model = genai.GenerativeModel(
            model_name=MODEL_ID,
            system_instruction=system_instruction
        )

        with st.chat_message("assistant"):
            # 過去の履歴を含めて会話
            chat = model.start_chat(history=[
                {"role": m["role"], "parts": [m["content"]]} for m in st.session_state.messages[:-1]
            ])
            
            response = chat.send_message(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            res_data = json.loads(response.text)
            reply_text = res_data.get("reply", "申し訳ありません。もう一度お話しいただけますか？")

            st.markdown(reply_text)
            
            # リスク対応
            if risk_level >= 4:
                st.error("⚠️ 大切なあなたへ：一人で抱え込まないでください。")
                st.info("24時間子供SOSダイヤル: 0120-0-78310")

            st.session_state.messages.append({"role": "assistant", "content": reply_text})

    except Exception as e:
        st.error(f"接続エラーが発生しました。時間を置いてから再度お試しください。")
        # 詳細なエラーをデバッグ用に隠しておく
        with st.expander("エラー詳細"):
            st.write(str(e))

# セッションが長くなった場合のサマリー機能
if len(st.session_state.messages) > 6:
    st.divider()
    if st.button("📝 今日の相談を振り返る"):
        with st.status("カウンセリング・ノートを作成中..."):
            summary_model = genai.GenerativeModel(model_name=MODEL_ID)
            summary_res = summary_model.generate_content(
                f"以下の対話から、相談者の頑張りや変化を認める温かい要約を作成してください。\n対話履歴: {str(st.session_state.messages)}"
            )
            st.success("今日のまとめ")
            st.write(summary_res.text)