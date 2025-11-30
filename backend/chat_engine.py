import os
import time
import json
import streamlit as st
from cerebras.cloud.sdk import Cerebras
from utils.tools import (
    search_via_perplexity, 
    read_web_page, 
    python_calculator,
    TOOLS_SCHEMA
)

@st.cache_resource
def get_cerebras_client():
    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        raise RuntimeError("CEREBRAS_API_KEY が .env に設定されていません。")
    return Cerebras(api_key=api_key)

def chat_with_cerebras(messages, model_id, is_idea_mode):
    """
    Cerebrasとのチャットを実行する。
    Idea Modeの場合はツール群の使用を許可し、必要に応じてループ処理を行う。
    """
    client = get_cerebras_client()
    tools = TOOLS_SCHEMA if is_idea_mode else None
    
    start_time = time.time()
    
    # 1st Pass
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            tools=tools,
            temperature=0.8 if is_idea_mode else 0.1,
            max_completion_tokens=2048
        )
    except Exception as e:
        return f"Error (Cerebras): {e}", [], 0

    msg = response.choices[0].message
    tool_outputs = []
    final_content = ""

    # Tool Call Handling
    if msg.tool_calls:
        messages.append(msg) # アシスタントのツール呼び出し意図を履歴へ
        
        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            result = ""
            
            try:
                if fn_name == "search_via_perplexity":
                    query = args["query"]
                    st.toast(f"🕵️‍♀️ Searching: {query}")
                    result = search_via_perplexity(query)
                    tool_outputs.append({"type": "search", "query": query, "result": result})

                elif fn_name == "read_web_page":
                    url = args["url"]
                    st.toast(f"📖 Reading: {url}")
                    result = read_web_page(url)
                    tool_outputs.append({"type": "read", "url": url, "result": result[:200] + "..."}) # UI表示用は短く

                elif fn_name == "python_calculator":
                    code = args["code"]
                    st.toast("🧮 Calculating...")
                    result = python_calculator(code)
                    tool_outputs.append({"type": "calc", "code": code, "result": result})
                
                else:
                    result = f"Error: Unknown tool '{fn_name}'"

            except Exception as e:
                result = f"Error executing {fn_name}: {str(e)}"

            # 結果を履歴に追加
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result)
            })
        
        # 2nd Pass (with Tool Results)
        try:
            final_response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                # tools=None, # 2回目はループ防止のためツール無効化（必要なら回数制限付きループにする）
                temperature=0.8,
                max_completion_tokens=2048
            )
            final_content = final_response.choices[0].message.content
        except Exception as e:
            final_content = f"Error (Cerebras 2nd pass): {e}"

    else:
        final_content = msg.content

    end_time = time.time()
    latency = end_time - start_time
    
    # メタ情報付与
    final_content += f"\n\n*(Thought Time: {latency:.4f}s)*"

    return final_content, tool_outputs, latency