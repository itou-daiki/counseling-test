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

# --- 2. UI設計（モバイル・エラー防止） ---
st.set_page_config(page_title="心の相談室", page_icon="🤝", layout="centered")

st.markdown("""
    <style>
    .stApp { max-width: 800px; margin: 0 auto; }
    .stButton>button { width: 100%; border-radius: 20px; height: 3em; margin-top: 10px; }
    .stChatMessage { border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤝 心の相談室")

with st.expander("⚙️ 初期設定・使い方", expanded=False):
    api_key = st.text_input("Gemini API Key", type="password")
    st.markdown("[👉 APIキーを取得（無料）](https://aistudio.google.com/app/apikey)")
    if st.button("対話をリセット"):
        st.session_state.messages = []
        st.rerun()

if not api_key:
    st.info("上の「初期設定」からAPIキーを入力して、話を始めてください。")
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

# --- 3. メインロジック（エラー修正済み） ---

if prompt := st.chat_input("今、どんなお気持ちですか？"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    risk_level = detect_risk_level(prompt)

    system_instruction = f"""
    あなたは、経験豊富なスクールカウンセラーです。来談者中心療法とマイクロカウンセリングの技法を使います。
    【指針】
    1. 感情の反射：言葉の裏にある感情を汲み取り、言語化を助けます。
    2. 評価しない：良い・悪いという判断をせず、ありのままを受け止めます。
    3. 安全確保：リスクレベルが「{risk_level}」であることを踏まえ、レベル4以上なら専門機関への連絡を促します。

    【形式: JSONのみ】
    {{
        "analysis": "心理分析",
        "reply": "カウンセラーとしての返答"
    }}
    """

    try:
        model = genai.GenerativeModel(
            model_name=MODEL_ID,
            system_instruction=system_instruction
        )

        # 【重要：ここを修正】Streamlitの 'assistant' を API用の 'model' に変換
        history_for_api = []
        for m in st.session_state.messages[:-1]: # 最後の自分の発言以外
            role = "model" if m["role"] == "assistant" else "user"
            history_for_api.append({"role": role, "parts": [m["content"]]})

        with st.chat_message("assistant"):
            chat = model.start_chat(history=history_for_api)
            
            response = chat.send_message(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            res_data = json.loads(response.text)
            reply_text = res_data.get("reply", "...")

            st.markdown(reply_text)
            
            if risk_level >= 4:
                st.error("⚠️ 一人で抱え込まないでください。24時間子供SOSダイヤル: 0120-0-78310")

            st.session_state.messages.append({"role": "assistant", "content": reply_text})

    except Exception as e:
        st.error("エラーが発生しました。時間を置いて再度お試しください。")
        with st.expander("技術的な詳細"):
            st.code(str(e))

# 振り返り機能
if len(st.session_state.messages) > 6:
    st.divider()
    if st.button("📝 今日の相談を振り返る"):
        summary_model = genai.GenerativeModel(model_name=MODEL_ID)
        summary_res = summary_model.generate_content(
            f"対話履歴を元に、相談者の気持ちを整理する温かいメッセージを作成してください。: {str(st.session_state.messages)}"
        )
        st.success("今日のまとめノート")
        st.write(summary_res.text)