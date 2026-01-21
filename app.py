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
    """キーワードによる即時リスク判定"""
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
    
    # モデル選択の動的化（404回避のため）
    st.divider()
    model_option = st.selectbox(
        "使用モデルの選択",
        ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-8b"],
        index=0,
        help="最新の2.0-flashを推奨します。エラーが出る場合は1.5系を試してください。"
    )

    if st.button("会話履歴をリセット"):
        st.session_state.messages = []
        st.rerun()

st.title("🌱 安心相談チャット")
st.caption("2026年度版：最新のGemini 2.0エンジンを搭載した学生相談システム")

if not api_key:
    st.warning("サイドバーにAPIキーを入力してください。")
    st.stop()

# APIの初期化
genai.configure(api_key=api_key)

if "messages" not in st.session_state:
    st.session_state.messages = []

# チャット履歴表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 3. メインロジック ---
if prompt := st.chat_input("今、どんなことを考えていますか？"):
    # ユーザー入力を表示
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # リスクレベルの判定
    risk_level = detect_risk_level(prompt)

    # 1回のリクエストで「分析」と「回答」を同時に行うシステムプロンプト
    system_instruction = f"""
    あなたは温かいプロのスクールカウンセラーです。
    
    【厳守事項】
    1. 相談者のニーズ（傾聴・改善策・共考）を文脈から分析してください。
    2. 現在のリスクレベルは「{risk_level}」です。
    3. レベル4以上の場合は、専門窓口（24時間子供SOS等）への相談を優しく勧めてください。
    4. 出力は以下のJSON形式のみとし、余計な説明は省いてください。
    {{
        "needs": "傾聴 または 改善策 または 共考",
        "reply": "相談者への親身な回答（5段階のリスクに応じたトーン）"
    }}
    """

    try:
        # モデルの構築
        model = genai.GenerativeModel(
            model_name=model_option,
            system_instruction=system_instruction
        )

        with st.chat_message("assistant"):
            # JSONモードで生成
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            # 結果の解析と表示
            res_data = json.loads(response.text)
            reply_text = res_data.get("reply", "...")
            
            st.markdown(reply_text)
            
            # リスクレベルが高い場合の補助UI
            if risk_level >= 4:
                st.error("⚠️ 一人で抱え込まずに、相談してみませんか？")
                st.info("24時間子供SOSダイヤル: 0120-0-78310")

            # 履歴に保存
            st.session_state.messages.append({"role": "assistant", "content": reply_text})

    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            st.error(f"モデル '{model_option}' が見つかりませんでした。サイドバーで別のモデルを選択するか、ライブラリを更新してください。")
        elif "429" in error_msg:
            st.error("混雑しています。1分ほど待ってから再度送信してください。")
        else:
            st.error(f"予期せぬエラーが発生しました: {error_msg}")