# 🦄 StartUp DOJO / Legal Sanctuary

起業アイデアを鬼メンターにしごかれながら磨き上げ、同時に法務リスクもケアするための RAG + LLM アプリです。

- UI: Streamlit チャット（Idea Mode: "🦄 UNICORN DOJO" / Legal Mode: "⚖️ LEGAL SANCTUARY"）
- モデル: Cerebras Cloud の LLM（`CEREBRAS_API_KEY` が必要）
- ベクトルDB: Qdrant（このリポジトリには既に `qdrant_storage/` が同梱済み）
- 検索/ツール: Perplexity, Jina Reader, Python電卓ツール（Idea Modeで使用）

公開リポジトリとして、クローンして `.env` を用意すれば、Raspberry Pi 5 でもワンコマンドで立ち上がる構成になっています。

---

## 🏁 クイックスタート（Raspberry Pi 5 推奨）

### 前提条件

- 64bit OS の Raspberry Pi 5（メモリ 4GB 以上推奨）
- Docker ＋ Docker Compose がインストール済み

### 1. リポジトリをクローン

```bash
git clone https://github.com/Mori-kamiyama/startup-dojo.git
cd startup-dojo
```

### 2. `.env` を作成（APIキー）

プロジェクト直下に `.env` を作ります:

```env
CEREBRAS_API_KEY=your_cerebras_key
PERPLEXITY_API_KEY=your_perplexity_key
JINA_API_KEY=your_jina_key          # 任意
HF_TOKEN=your_huggingface_token     # embeddinggemma 用に推奨
```

### 3. ワンコマンド起動

```bash
bash run.sh
```

- `qdrant` コンテナが立ち上がり、ローカルの `./qdrant_storage` ディレクトリがそのままマウントされます。
- `app` コンテナがビルドされ、Streamlit アプリが `http://<ラズパイのIP>:8501` で利用できます。

停止するときは `Ctrl + C` で抜けたあと、必要なら次でコンテナを落とせます:

```bash
docker compose down
```

---

## 🧩 アーキテクチャ概要

- `main.py`
  - Streamlit アプリ本体。Idea Mode / Legal Mode を切り替え、チャット UI を提供。
- `backend/rag_engine.py`
  - SentenceTransformers + Qdrant を使った RAG 部分（Law / Idea コレクション）。
- `backend/chat_engine.py`
  - Cerebras Cloud SDK を叩いてチャット生成。Idea Mode では外部ツール呼び出しをサポート。
- `utils/tools.py`
  - Perplexity 検索、Jina Reader、Python 電卓などのツール定義。
- `utils/prompts.py`
  - 鬼メンター（StartUp DOJO）と法務執事（Legal Sanctuary）のプロンプトテンプレート。
- `qdrant_storage/`
  - 既に計算済みのベクトルデータ（法令・フレームワークなど）を含む Qdrant のストレージ。

環境変数は `config.py` から読み込まれます:

- `CEREBRAS_API_KEY`, `PERPLEXITY_API_KEY`, `JINA_API_KEY`, `HF_TOKEN`
- `QDRANT_HOST`（デフォルト: `localhost`）
- `QDRANT_PORT`（デフォルト: `6333`）

Docker Compose では、`QDRANT_HOST=qdrant` として同一ネットワーク内の Qdrant コンテナへ接続しています。

---

## 🧪 ローカル開発（任意）

Docker を使わず開発したい場合の目安です。

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install uv || true
pip install -e .

# 別途 Qdrant を立ち上げた状態で
streamlit run main.py
```

`config.py` の `QDRANT_HOST` / `QDRANT_PORT` を、手元の Qdrant の接続先に合わせてください。

---

## 🧭 開発メモ: Legal Mode ロードマップ

このセクションは、Legal Mode（法務RAG）の設計メモとして残しています。

### 🗺️ Legal Mode 開発ロードマップ

#### Phase 1: データの取得と整備（ここが品質の8割を決める）
法律RAGにおいて、データが汚いと絶対にまともな回答は出ません。

1.  **対象法令の選定**
    * まずは「スタートアップ三種の神器」に絞ることを推奨。
        * **会社法**（設立・組織運営）
        * **労働基準法**（雇用・解雇・賃金）
        * **特定商取引法**（Webサービス運営・広告）
2.  **一次情報の取得 (e-Gov法令検索)**
    * **e-Gov法令API** または **一括ダウンロード機能** を使って、XML形式のデータを取得する。
        * *※HTMLスクレイピングは構造が崩れるので非推奨です。*
3.  **【最重要】構造化データの作成 (前処理)**
    * XMLを解析し、Pythonスクリプトで以下の構造を持ったJSON等の形式に変換する。
    * ただ文字数で切るのではなく、**「一条」を一つの塊（Chunk）」**にする。
    * **メタデータの付与:** 各チャンクに以下を付与する。
        * `law_name`: "会社法"
        * `article_id`: "第〇条"
        * `category`: "設立" など（可能なら）
        * `text`: 条文の本文

#### Phase 2: RAGエンジンの構築 (Backend)
検索精度を高めるための仕組みを作ります。

4.  **ベクトルデータベースの準備**
    * **Qdrant** (推奨・高速/高機能) または **Chroma** をローカル（Docker等）で立ち上げる。
5.  **Embeddings（埋め込み）の実装**
    * 日本語に強いモデルを選定して実装。
        * OpenAI `text-embedding-3-small` (コスト安・精度良)
        * または `intfloat/multilingual-e5-large` (ローカル実行)
6.  **ハイブリッド検索の実装**
    * **意味検索 (Vector)**: 「解雇したい」→ 第20条（解雇予告）をヒットさせる。
    * **キーワード検索 (BM25)**: 「36協定」→ 正確にその単語を含む条文をヒットさせる。
    * この2つを組み合わせる（Reciprocal Rank Fusionなど）ロジックを組む。
7.  **リランク (Rerank) の導入**
    * 検索で多め（Top 20件くらい）に取得し、**Cohere Rerank** 等を使って「質問との関連度順」に並び替え、Top 5件に絞る処理を入れる。

#### Phase 3: 生成AIとの接続 (Agent)
検索した結果を元に、それっぽい回答を作らせます。

8.  **プロンプトエンジニアリング**
    * **System Prompt:** 「あなたは優秀な弁護士です。提供された条文**のみ**を根拠に回答してください。個別の法律相談には乗れない旨の免責事項を添えてください。」
    * **引用の実装:** 回答文中に `[出典: 労働基準法 第20条]` のようにソースを明記させる指示を入れる。
9.  **LangChain / LlamaIndex でチェーン構築**
    * `ユーザの質問` → `検索クエリ生成` → `ハイブリッド検索 + リランク` → `LLMで回答生成` という一連の流れをコード化する。

#### Phase 4: UI統合とテスト (Frontend & Eval)

10. **StreamlitでのUI実装**
    * チャット画面を作成。
    * 「Legal Mode」であることを示すUI（テーマカラーを変える、アイコンを出すなど）。
    * 回答の下に「参照した条文」をアコーディオン等で表示する機能。
11. **評価 (Evaluation)**
    * **Ragas** などの評価フレームワークを使うか、自分で「想定問答集（Ground Truth）」を20個ほど作り、正しく条文を引けているかテストする。

---

### 🛠️ まず今日やるべきアクション

まずは **Phase 1 の「データ取得と構造化」** です。ここができないと何も始まりません。

**Step 1:**
PCに作業用フォルダを作り、Python環境（`venv`など）を用意する。

**Step 2:**
以下のURL（e-Gov法令検索）から、**「会社法」**のデータを取得してみる。
* 一番手っ取り早いのは、e-Govの「ダウンロード」からXMLを取得することですが、まずは手動でテキストをコピペして、テキストファイル(`kaisha_ho.txt`)を作ってみるだけでもOKです。

**Step 3:**
それをPythonで読み込み、「第○条」ごとのリストにするコードを書く。

--
