import streamlit as st
import random
from config import (
    CEREBRAS_MODEL_CHOICES, 
    ANALYSIS_STEPS
)
from backend.rag_engine import get_retrieval_resources, build_system_prompt
from backend.chat_engine import chat_with_cerebras

# --- Session State Initialization ---
def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Initial Message
        st.session_state.messages.append({
            "role": "assistant", 
            "content": "ようこそ、起業家の卵よ。準備運動は済んだか？\n\nまずは**アイデアを一言**置いていけ。そこから全てが始まる。"
        })
    
    if "current_step_id" not in st.session_state:
        st.session_state.current_step_id = 1 # STEEP分析から開始

# --- UI Components ---
def render_sidebar():
    st.sidebar.markdown("## ⚙️ Cockpit Settings")
    
    # Mode Selection
    mode = st.sidebar.radio(
        "パートナーを選択", 
        ["🔥 鬼メンター (Idea Mode)", "🛡️ 法務の守護神 (Legal Mode)"],
        captions=["シリコンバレーの風を浴びる", "コンプライアンスの盾を構える"]
    )
    
    st.sidebar.markdown("---")
    
    # Model & Retrieval Settings
    cerebras_model_id = st.sidebar.selectbox("Brain (Model)", CEREBRAS_MODEL_CHOICES, index=0)
    top_k = st.sidebar.slider("知識レベル (Retrieval Depth)", 1, 10, 3)
    
    # Analysis Step Indicator (Only for Idea Mode)
    if "Idea" in mode:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🏋️‍♂️ Training Menu")
        current_id = st.session_state.current_step_id
        for step_id, step_name in ANALYSIS_STEPS.items():
            if step_id == current_id:
                st.sidebar.markdown(f"**👉 {step_id}. {step_name} (NOW)**")
            elif step_id < current_id:
                st.sidebar.markdown(f"✅ {step_id}. {step_name}")
            else:
                st.sidebar.markdown(f"⬜ {step_id}. {step_name}")

        if st.sidebar.button("Step Reset 🔄"):
            st.session_state.current_step_id = 1
            st.rerun()
            
    return mode, cerebras_model_id, top_k

def render_next_move_buttons(mode):
    """動的に次のアクションボタンを生成する"""
    if "Idea" not in mode:
        return

    st.write("---")
    st.markdown("##### 👉 Next Move: 次の一手を選べ")
    
    current_id = st.session_state.current_step_id
    next_step_name = ANALYSIS_STEPS.get(current_id + 1, "コンプリート")
    current_step_name = ANALYSIS_STEPS.get(current_id, "不明")

    cols = st.columns(3)
    
    # Button 1: Proceed to Next Step
    if current_id < 10:
        if cols[0].button(f"💪 次へ: {next_step_name}"):
            st.session_state.current_step_id += 1
            next_input = f"よし、次のメニュー「{next_step_name}」に進みたい。俺のアイデアをこのフレームワークで叩き直してくれ。"
            handle_user_input(next_input, mode, st.session_state.cerebras_model_id, st.session_state.top_k)
            st.rerun()
    else:
        if cols[0].button("🏆 免許皆伝"):
            st.balloons()
            st.success("お前はもう一人前だ。現場（マーケット）へ行け！")

    # Button 2: Deep Dive Current Step
    if cols[1].button(f"🔎 深掘り: {current_step_name}"):
        deep_input = f"今の「{current_step_name}」がまだ甘い気がする。もっと容赦なく、詳細に分析してくれ。"
        handle_user_input(deep_input, mode, st.session_state.cerebras_model_id, st.session_state.top_k)
        st.rerun()

    # Button 3: Exit / Reset
    if cols[2].button("🛌 休憩 (サウナ)"):
        st.info("いい判断だ。休息も仕事のうち。脳を冷やして出直してこい。")


def handle_user_input(user_input, mode, cerebras_model_id, top_k):
    # Add User Message
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.status("🚀 起業家精神を注入中... (Processing)", expanded=True) as status:
        st.write("🔍 知識ベースを検索中...")
        # Resources
        model, qdrant_client = get_retrieval_resources()

        # System Prompt Builder
        current_phase = ANALYSIS_STEPS.get(st.session_state.current_step_id, "自由分析")
        system_prompt, results = build_system_prompt(
            user_input, mode, current_phase, model, qdrant_client, cerebras_model_id, top_k
        )
        
        st.write("🧠 AIブレインストーミング中...")
        # Prepare Messages for API
        api_messages = [{"role": "system", "content": system_prompt}]
        # History Window (Keep last 10 turns to save tokens)
        for m in st.session_state.messages[-10:]:
            if m["role"] != "tool":
                 api_messages.append(m)

        # Call Chat Engine
        response_text, tool_outputs, latency = chat_with_cerebras(
            api_messages, cerebras_model_id, is_idea_mode=("Idea" in mode)
        )
        
        status.update(label="完了! (Finished)", state="complete", expanded=False)

    # Add Assistant Message
    st.session_state.messages.append({"role": "assistant", "content": response_text})
    
    # Store Metadata for displaying later (optional, simplistic approach here)
    st.session_state.last_results = results
    st.session_state.last_tool_outputs = tool_outputs


# --- Main Entry Point ---
def main():
    st.set_page_config(page_title="StartUp Dojo AI", page_icon="🦄", layout="wide")
    
    # Custom CSS
    st.markdown("""
    <style>
    .stChatInput textarea { font-size: 1.1rem; }
    .stMarkdown h1 { font-family: 'Helvetica Neue', sans-serif; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

    init_session_state()
    
    # Sidebar & Settings
    mode, cerebras_model_id, top_k = render_sidebar()
    # Store in session for callback access
    st.session_state.cerebras_model_id = cerebras_model_id
    st.session_state.top_k = top_k

    # Header
    if "Idea" in mode:
        st.title("🦄 UNICORN DOJO")
        st.markdown(f"**Current Phase: {ANALYSIS_STEPS.get(st.session_state.current_step_id)}**")
        input_placeholder = "アイデアを投げ込め、または指示を出せ..."
    else:
        st.title("⚖️ LEGAL SANCTUARY")
        st.markdown("**法務リスクの防波堤**")
        input_placeholder = "契約書の条項や懸念点を入力..."

    # Display History
    for msg in st.session_state.messages:
        if msg["role"] == "tool": continue
        
        avatar = "👤"
        if msg["role"] == "assistant":
            avatar = "😈" if "Idea" in mode else "🧐"
        
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # Chat Input
    if prompt := st.chat_input(input_placeholder):
        # Display user message immediately
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
            
        handle_user_input(prompt, mode, cerebras_model_id, top_k)
        st.rerun()

    # Render Results (RAG & Tools) for the *last* message if available
    # Note: This is a simple way to show context. A more robust way is to attach context to message history objects.
    if hasattr(st.session_state, 'last_results') and st.session_state.last_results:
        expander_title = "🧠 脳内参照データ (RAG)" if "Idea" in mode else "📚 参照法令・判例"
        with st.expander(expander_title):
            for res in st.session_state.last_results:
                payload = res.payload
                title = payload.get("title") or f"{payload.get('law_name')} {payload.get('article_id')}"
                st.markdown(f"- **{title}** (Relevance: {res.score:.3f})")
                st.caption(payload.get("text", "")[:100] + "...")
            # Clear to avoid showing on refresh without new input (Optional)
            # st.session_state.last_results = None 

    # Next Actions
    render_next_move_buttons(mode)

if __name__ == "__main__":
    main()