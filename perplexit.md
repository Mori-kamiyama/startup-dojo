実装を詳しく検討するために、**「Cerebras (LLM) + RAG (内部知識) + Perplexity (外部検索)」を組み合わせたハイブリッド・エージェント構成**の概要をまとめます。

この実装により、あなたのアプリは「理論（フレームワーク）」と「現実（最新の市場データ）」の両方を持った、逃げ場のない最強の壁打ち相手になります。

-----

### 🏛️ 実装アーキテクチャ概要

処理の流れを一直線（リニア）から、\*\*「判断とループ」\*\*のある構造に変更します。

1.  **User**: 「猫の翻訳アプリを作りたい」
2.  **RAG (Local)**: 「リーンキャンバス」「ペルソナ分析」の知識を取得。
3.  **Cerebras (1回目 - 司令塔)**:
      * 知識とユーザーの入力を分析。
      * 「競合がいるか確認が必要だ」と判断 → **ツール呼び出し (Tool Call)** を発行。
4.  **Python (Tool Execution)**:
      * Perplexity APIを叩く（`query: "猫 翻訳アプリ 競合"`）。
      * PerplexityがWeb検索し、最新情報を要約して返す。
5.  **Cerebras (2回目 - 鬼メンター)**:
      * [ユーザーの入力] + [RAGの理論] + [Perplexityの検索結果] を統合。
      * 「理論的には良いが、既に『MeowTalk』という競合がいるぞ。どう差別化する？」と回答。

-----

### 🛠️ 必要な3つの構成要素

実装には以下の3つのパーツが必要です。

#### 1\. 外部ツール関数（The Hand）

Perplexity APIを実際に叩いて結果を返すPython関数です。

  * **役割**: 指定されたクエリで検索し、テキストを返す。
  * **使用モデル**: `llama-3.1-sonar-large-128k-online` (検索特化モデル)。

#### 2\. ツール定義スキーマ（The Manual）

Cerebras (LLM) に「自分にはどんな道具（ツール）があり、どう使うのか」を教えるJSON定義書です。

  * **OpenAI互換形式**: `tools = [{ "type": "function", ... }]`
  * **記述内容**: 「市場調査や競合比較が必要な時に使え」という指示を含める。

#### 3\. 実行ループ（The Brain）

LLMの出力を監視し、回答なら表示、ツール呼び出しなら実行して再入力するロジックです。

-----

### 💻 実装ブループリント（コード設計図）

`st.chat_input` が入った後の処理フローの詳細です。

#### A. ツールの準備（関数の定義）

```python
def search_via_perplexity(query: str):
    """Perplexity APIを叩いて検索結果を返す"""
    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": "llama-3.1-sonar-large-128k-online",
        "messages": [
            {"role": "system", "content": "最新の市場調査レポートとして簡潔に回答せよ。"},
            {"role": "user", "content": query}
        ]
    }
    # ... requests.post ...
    return response_text
```

#### B. ツール定義（Schema）

```python
tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "search_via_perplexity",
            "description": "ユーザーのアイデアに関連する【競合他社、市場規模、トレンド】をWeb検索する時に使用する。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "検索キーワード"}
                },
                "required": ["query"]
            }
        }
    }
]
```

#### C. メインループのロジック（ここが肝）

```python
# 1. コンテキストの準備
# システムプロンプト(RAG結果含む) + 過去の会話履歴
messages = [{"role": "system", "content": rag_system_prompt}] + history

# 2. 最初の推論 (First Pass)
response = cerebras.chat.completions.create(
    model="llama-3.3-70b",
    messages=messages,
    tools=tools_schema  # ★ツールを渡す
)
msg = response.choices[0].message

# 3. 分岐判定
if msg.tool_calls:
    # --- 🅰️ 検索が必要な場合 ---
    
    # ユーザーへのUI演出
    st.write("🕵️‍♀️ 競合を特定中...") 

    # ツール実行
    tool_call = msg.tool_calls[0]
    args = json.loads(tool_call.function.arguments)
    search_result = search_via_perplexity(args["query"])

    # 履歴に追加
    # (1) アシスタントの「検索したい」という意図
    messages.append(msg)
    # (2) ツールの「検索結果」
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": search_result
    })

    # 4. 最終推論 (Second Pass)
    # 検索結果を踏まえて、もう一度LLMに回答させる
    final_response = cerebras.chat.completions.create(
        model="llama-3.3-70b",
        messages=messages
        # ここではtoolsは渡さない（無限ループ防止）
    )
    final_content = final_response.choices[0].message.content

else:
    # --- 🅱️ 検索不要（通常の会話）の場合 ---
    final_content = msg.content

# 5. 結果表示
st.markdown(final_content)
```

-----

### 🧠 鬼メンターのプロンプト調整

検索ツールを持たせただけでは不十分です。「得られた情報をどう使うか」をシステムプロンプト（Idea Mode）に追加する必要があります。

> **追加する指示:**
> 「もし検索ツールを使用した場合は、その検索結果（競合や市場データ）を**証拠**として使い、ユーザーのアイデアの甘さを徹底的に論破せよ。単なる検索結果の要約はするな。それを武器にフィードバックしろ。」

### ⚠️ 注意点・考慮事項

1.  **レイテンシ（待ち時間）**:
      * Cerebrasは爆速ですが、Perplexityの検索には数秒かかります。Streamlit上で `st.spinner("市場データを収集中...")` などを出して、ユーザーを飽きさせない演出が必須です。
2.  **コンテキスト長**:
      * 検索結果（Perplexityの回答）が長すぎると、トークンを消費しすぎます。Perplexityへのシステムプロンプトで「簡潔に要点を絞って」と指示するか、Python側で文字数カット処理を入れると安全です。
3.  **エラーハンドリング**:
      * Perplexity APIがダウンしている場合やタイムアウトした場合、アプリが落ちないように `try-except` で囲み、「検索に失敗しましたが、私の知識で回答します」とフォールバックする処理を入れてください。

これで、**「既存知識(RAG)」×「最新情報(Search)」×「高速推論(Cerebras)」** という強力な構成になります。実装を進めますか？