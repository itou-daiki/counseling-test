import streamlit as st
import google.generativeai as genai
import re

# --- 設定・定数 ---
RISK_KEYWORDS = {
    5: ["死にたい", "自殺", "消えたい", "殺す", "自傷", "リスカ"],
    4: ["学校に行けない", "不登校", "いじめ", "暴力", "虐待", "限界", "眠れない"],
    3: ["辛い", "苦しい", "やめたい", "不安", "逃げたい"],
    2: ["悩んでいる", "困っている", "イライラ", "集中できない"],
    1: []  # デフォルト
}

# --- ヘルパー関数 ---

def detect_risk_level(text):
    """キーワードに基づいた5段階のリスクレベル判定"""
    for level in range(5, 0, -1):
        if any(keyword in text for keyword in RISK_KEYWORDS.get(level, [])):
            return level
    return 1

def analyze_needs_with_ai(model, user_input):
    """Geminiを使用して相談者のニーズを判定"""
    analysis_prompt = f"""
    以下の相談内容から、相談者が求めている支援の種類を1つ選んで回答してください。
    回答は【傾聴】【改善策】【共考】のいずれか1単語のみとしてください。

    【傾聴】：ただ話を聞いてほしい、気持ちを受け止めてほしい
    【改善策】：具体的なアドバイスや解決方法を教えてほしい
    【共考】：一緒にこれからの行動や選択肢を考えてほしい

    相談内容：{user_input}
    """
    try:
        response = model.generate_content(analysis_prompt)
        content = response.text.strip()
        if "傾聴" in content: return "傾聴"
        if "改善策" in content: return "改善策"
        if "共考" in content: return "共考"
        return "傾聴" # デフォルト
    except:
        return "傾聴"

def get_system_instruction(risk_level, needs):
    """リスクレベルとニーズに応じた動的システムプロンプトの生成"""
    
    # 基本ガードレール
    base_instruction = (
        "あなたはプロのスクールカウンセラーとして、学生に寄り添った対話を行います。"
        "批判や否定は一切せず、まずは相談者の感情を肯定的に受け止めてください。"
        "不適切なアドバイスや、医療行為に該当する診断は行わないでください。"
    )

    # ニーズ別の振る舞い
    needs_map = {
        "傾聴": "感情の反映（オウム返し）や共感的な相槌を重視し、相談者が話しやすい雰囲気を作ってください。",
        "改善策": "相談者の状況を整理し、具体的で小さなステップから始められる解決策を提案してください。",
        "共考": "「どうしたいか」を問いかけながら、複数の選択肢を一緒に検討し、相談者の自己決定を促してください。"
    }

    # リスクレベル別の振る舞い
    if risk_level >= 4:
        risk_instruction = (
            "【重要】相談者の生命や安全にリスクがある状態です。"
            "寄り添いつつも、一人で抱え込まずに学校の保健室、教育相談センター、"
            "または専門の相談窓口（24時間子供SOSダイヤル等）へ連絡することを強く、優しく勧めてください。"
        )
    else:
        risk_instruction = needs_map.get(needs, "")

    return f"{base_instruction}\n\n現在の状況方針：{risk_instruction}"

# --- UI (Streamlit) ---

st.set_page_config(page_title="学生相談サポートAI", page_icon="🌱")

st.title("🌱 安心相談チャット")
st.caption("他者の目を気にせず、あなたの今の気持ちを教えてください。")

# サイドバーでAPIキー入力
with st.sidebar:
    st.header("設定")
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    st.info("入力された内容は、AIによるリスク分析と対話のためにのみ使用されます。")

if not api_key:
    st.warning("サイドバーからGoogle AI (Gemini) のAPIキーを入力してください。")
    st.stop()

# モデルの初期化
genai.configure(api_key=api_key)
model_name = "gemini-2.0-flash"

# セッション状態の初期化
if "messages" not in st.session_state:
    st.session_state.messages = []

# チャット履歴の表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 相談入力
if prompt := st.chat_input("今、どんなことを考えていますか？"):
    # 1. ユーザーメッセージの表示
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. リスクとニーズの分析
    risk_level = detect_risk_level(prompt)
    
    # 分析用の一時的なモデル呼び出し
    temp_model = genai.GenerativeModel(model_name)
    needs = analyze_needs_with_ai(temp_model, prompt)

    # 3. システム命令の構築
    system_instruction = get_system_instruction(risk_level, needs)
    
    # 4. 回答生成
    chat_model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_instruction
    )
    
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        # 履歴を含めて送信
        chat_session = chat_model.start_chat(
            history=[{"role": m["role"], "parts": [m["content"]]} for m in st.session_state.messages[:-1]]
        )
        
        try:
            response = chat_session.send_message(prompt, stream=True)
            for chunk in response:
                full_response += chunk.text
                response_placeholder.markdown(full_response + "▌")
            
            # リスクレベルが高い場合のアラート表示
            if risk_level >= 4:
                st.error("⚠️ 一人で悩まずに、専門の窓口も利用してみませんか？（画面下部に相談先リンクを表示しています）")
            
            response_placeholder.markdown(full_response)
        except Exception as e:
            st.error(f"エラーが発生しました: {str(e)}")
            full_response = "申し訳ありません。現在お答えすることができません。少し時間を置いてから再度お試しください。"

    st.session_state.messages.append({"role": "assistant", "content": full_response})

# 画面下部に相談先情報を固定（レベル4・5向け）
if any(detect_risk_level(m["content"]) >= 4 for m in st.session_state.messages if m["role"] == "user"):
    with st.expander("📌 大切なあなたへ：専門の相談窓口案内", expanded=True):
        st.markdown("""
        - **24時間子供SOSダイヤル**: 0120-0-78310
        - **チャット相談**: [SNS相談などの紹介（厚生労働省）](https://www.mhlw.go.jp/mamoruchat/)
        - **校内窓口**: 保健室の先生やスクールカウンセラーに「AI相談でここを勧められた」と伝えてみてください。
        """)