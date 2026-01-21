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

# --- 2. 専門的なUI設計 ---
st.set_page_config(page_title="プロフェッショナル相談室", page_icon="🤝", layout="centered")

with st.sidebar:
    st.header("⚙️ システム設定")
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    st.markdown("### 🔑 APIキー取得先")
    st.markdown("[Google AI Studio](https://aistudio.google.com/app/apikey)")
    
    if st.button("セッションを終了して記録を消去"):
        st.session_state.clear()
        st.rerun()

st.title("🤝 プロフェッショナル・カウンセリング")
st.caption("2026年最新のカウンセリング・アルゴリズムを適用しています")

if not api_key:
    st.info("サイドバーからAPIキーを入力して、セッションを開始してください。")
    st.stop()

# モデルの固定
genai.configure(api_key=api_key)
MODEL_ID = "gemini-2.5-flash"

if "messages" not in st.session_state:
    st.session_state.messages = []
if "emotion_history" not in st.session_state:
    st.session_state.emotion_history = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 3. カウンセリング・プロトコルの実装 ---

if prompt := st.chat_input("今、あなたの心の中にあるものを教えてください"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    risk_level = detect_risk_level(prompt)

    # プロのカウンセラーとしての振る舞いを定義する高度なシステム命令
    system_instruction = f"""
    あなたは、公認心理師や臨床心理士の資格を持つベテランのスクールカウンセラーです。
    以下のカウンセリング・プロトコルを厳守してください。

    【基本的態度】
    1. 無条件の肯定的関心：相談者が何を言っても否定せず、一人の人間として尊重してください。
    2. 共感的理解：相談者の世界を、あたかも自分自身のもののように感じ、その理解を伝えてください。
    3. 自己一致：誠実で自然な態度で接してください。

    【技法】
    - 言い換え：相談者の言葉を別の表現で返し、理解を確認してください。
    - 感情の反射：言葉の裏にある「寂しさ」「怒り」「空虚感」などを汲み取り、言語化を助けてください。
    - 最小限の励まし：相槌だけでなく、話し続けやすい雰囲気を作ってください。

    【リスク対応】
    - 現在のリスクレベルは「{risk_level}」です。
    - レベル4以上の場合：受容しつつも、物理的な安全（信頼できる大人や専門機関への接続）を最優先したクロージングを行ってください。

    【出力形式：必ずJSONのみ】
    {{
        "analysis": "相談者の潜在的な心理状態の分析",
        "needs": "傾聴/改善策/共考",
        "reply": "プロのカウンセラーとしての返答（親しみやすさと専門性を両立）"
    }}
    """

    try:
        model = genai.GenerativeModel(
            model_name=MODEL_ID,
            system_instruction=system_instruction
        )

        with st.chat_message("assistant"):
            # 履歴を完全保持して文脈を重視
            chat = model.start_chat(history=[
                {"role": m["role"], "parts": [m["content"]]} for m in st.session_state.messages[:-1]
            ])
            
            response = chat.send_message(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            res_data = json.loads(response.text)
            analysis = res_data.get("analysis", "")
            reply_text = res_data.get("reply", "...")

            # 専門家としての分析を、相談者には「寄り添いの言葉」として提示
            st.markdown(reply_text)
            
            # リスクが高い場合の緊急UI
            if risk_level >= 4:
                st.divider()
                st.warning("あなたの安全を一番に考えさせてください。")
                st.error("24時間子供SOSダイヤル: 0120-0-78310")

            st.session_state.messages.append({"role": "assistant", "content": reply_text})
            st.session_state.emotion_history.append(analysis)

    except Exception as e:
        st.error("システムが一時的に不安定です。少しだけ深呼吸をして、もう一度試してみてください。")