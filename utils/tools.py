from openai import OpenAI
import os
import requests
import sys
import io
import contextlib
from config import PERPLEXITY_API_KEY, JINA_API_KEY

# --- 1. Perplexity Search ---
def search_via_perplexity(query: str):
    """Perplexity APIを叩いて検索結果を返す"""
    if not PERPLEXITY_API_KEY:
        return "Error: PERPLEXITY_API_KEY not found."
    
    client = OpenAI(api_key=PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")
    try:
        response = client.chat.completions.create(
            model="sonar-pro", 
            messages=[
                {"role": "system", "content": "最新の市場調査レポートとして、競合、市場規模、トレンドを具体的に回答せよ。出典も明記すること。"},
                {"role": "user", "content": query}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Search failed: {e}"

# --- 2. Jina Reader (URL Fetcher) ---
def read_web_page(url: str):
    """Jina Reader APIを使用してWebページの内容をMarkdownで取得する"""
    api_url = f"https://r.jina.ai/{url}"
    headers = {}
    if JINA_API_KEY:
        headers["Authorization"] = f"Bearer {JINA_API_KEY}"
    
    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        if response.status_code == 200:
            content = response.text
            # コンテンツが長すぎる場合は切り詰める
            return content[:10000] + "\n...(truncated)..." if len(content) > 10000 else content
        else:
            return f"Error fetching URL: Status {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error fetching URL: {e}"

# --- 3. Python Calculator ---
def python_calculator(code: str):
    """
    Pythonコードを実行して数値を計算する。
    注意: セキュリティリスクがあるため、信頼できる入力でのみ使用すること。
    """
    # 標準出力をキャプチャするためのバッファ
    buffer = io.StringIO()
    
    try:
        # print()の出力をbufferにリダイレクト
        with contextlib.redirect_stdout(buffer):
            # グローバル空間を制限し、計算に必要なライブラリのみ許可することも可能だが
            # ここではシンプルに実行する。
            exec_globals = {"__builtins__": __builtins__, "math": __import__("math")}
            exec(code, exec_globals)
        
        output = buffer.getvalue()
        return output.strip() if output else "No output (Did you forget to print?)"
    except Exception as e:
        return f"Calculation Error: {e}"

# --- Tool Definitions ---
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_via_perplexity",
            "description": "市場データ、競合他社、トレンド、最新ニュースなど、外部の最新情報が必要な場合に使用する。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "検索キーワード"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_web_page",
            "description": "特定のURLの内容を読み込んで分析する必要がある場合に使用する（例：競合のLP分析、ニュース記事の要約）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "読み込むWebページのURL"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "python_calculator",
            "description": "複雑な数値計算（LTV, CAC, 市場規模の推計など）を行う場合に使用する。Pythonコードを生成して実行する。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "実行するPythonコード。必ず結果を`print()`で出力すること。"}
                },
                "required": ["code"]
            }
        }
    }
]