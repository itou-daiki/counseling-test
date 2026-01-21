import streamlit as st
import google.generativeai as genai
import json

# --- 1. 定数・設定 ---
RISK_KEYWORDS = {
    5: ["死にたい", "自殺", "消えたい", "殺す", "自傷", "リスカ", "終わりにしたい"],
    4: ["学校に行けない", "不登校", "いじめ", "暴力", "虐待", "親に殴られる", "限界", "眠れない"],
    3: ["辛い", "苦しい", "やめたい", "不安", "逃げたい", "独りぼっち"],
    2: ["悩んでいる", "困っている", "イライラ", "集中できない", "やる気が出ない"],
    1: []
}

# --- 2. ロジック関数 ---

def detect_risk_level(text):
    """キーワードに基づいたリスク判定（即時判断用）"""
    for level in range(5, 0, -1):
        if any(keyword in text for keyword in RISK_KEYWORDS.get(level, [])):
            return level
    return 1

# --- 3. UI (Streamlit) ---

st.set_page_config(page_title="安心相談チャット", page_icon="🌱")

with st.sidebar:
    st.header("⚙️ 設定")
    # ユーザーがAPIキーを入力
    api_key = st.text_input("Gemini API Key", type="password")
    
    st.divider()
    st.markdown("### 🔑 APIキーの取得先")
    # APIキー取得先リンクの表示
    st.markdown("[Google AI Studioでキーを取得する](https://aistudio.google.com/app/apikey)")
    st.info("上記リンクからGoogleアカウントでログインし、『Get API key』をクリックして発行してください。")
    
    if st.button("会話をリセット"):
        st.session_state.messages = []
        st.rerun()

st.title("🌱 安心相談チャット")
st.caption("あなたの今の気持ちを、誰にも気兼ねせず話してみてください。")

if not api_key:
    st.warning("左側のサイドバーにAPIキーを入力してください。")
    st.stop()

# モデル設定（1.5-flashは無料枠制限が比較的緩やかです）
genai.configure(api_key=api_key)
model_name = "gemini-1.5-flash" 

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 4. 対話・分析処理 ---

if prompt := st.chat_input("どうしましたか？"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # ルールベースのリスク判定
    risk_level = detect_risk_level(prompt)

    # 1回のリクエストで判定と回答を両方行うためのシステムプロンプト
    system_instruction = f"""
    あなたは温かいプロのスクールカウンセラーです。
    
    【重要ルール】
    1. 相談者の発言から「ニーズ（傾聴・改善策・共考）」を分析してください。
    2. 現在のリスクレベルは「レベル{risk_level}」です。
    3. レベル4以上の場合は、寄り添いつつも専門機関への相談を促してください。
    4. 出力は必ず以下のJSON形式のみとし、他の文章は含めないでください。
    {{
        "needs": "傾聴 または 改善策 または 共考",
        "reply": "相談者への返答文章"
    }}
    """

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_instruction
    )

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        
        try:
            # APIリクエスト（JSONモード指定）
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            # 結果をパース
            res_data = json.loads(response.text)
            reply_text = res_data.get("reply", "うまくお答えできませんでした。もう一度お話しいただけますか？")
            
            # 回答を表示
            response_placeholder.markdown(reply_text)
            
            # リスクが高い場合の追加表示
            if risk_level >= 4:
                st.error("⚠️ 一人で抱え込まず、以下の窓口も検討してみてください。")
                st.markdown("- **24時間子供SOSダイヤル**: 0120-0-78310\n- **[SNS相談窓口](https://www.mhlw.go.jp/mamoruchat/)**")

            st.session_state.messages.append({"role": "assistant", "content": reply_text})

        except Exception as e:
            if "429" in str(e):
                st.error("【混雑エラー】APIの利用制限に達しました。1分ほど待ってから再度送信してください。")
            else:
                st.error(f"エラーが発生しました: {str(e)}")