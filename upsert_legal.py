import json
import os

import torch
from dotenv import load_dotenv
from huggingface_hub import login
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

# --- 設定 ---
CHUNK_DIR = "chunk"                          # 全ての JSON が入っているディレクトリ
COLLECTION_NAME = "legal_rag_gemma"          # コレクション名を変更
MODEL_ID = "google/embeddinggemma-300m"      # Googleの軽量モデル

# .env から環境変数を読み込む
load_dotenv()

def upsert_gemma():
    # 1. デバイス設定
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    # HF Token でログイン
    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
    if hf_token:
        print("Logging in to Hugging Face Hub...")
        login(token=hf_token)
    else:
        print("警告: HF_TOKEN / HUGGINGFACE_HUB_TOKEN が .env に設定されていません。")

    # 2. モデルのロード
    # trust_remote_code=True は念のため付けておきます
    print(f"Loading model: {MODEL_ID} ...")
    model = SentenceTransformer(MODEL_ID, device=device, trust_remote_code=True)

    # 3. データの読み込み（chunk/ 配下の全 JSON を一括読み込み）
    if not os.path.isdir(CHUNK_DIR):
        print(f"ディレクトリ '{CHUNK_DIR}' が見つかりません。")
        return

    json_files = sorted(
        f for f in os.listdir(CHUNK_DIR)
        if f.endswith(".json")
    )

    if not json_files:
        print(f"'{CHUNK_DIR}' に JSON ファイルがありません。")
        return

    chunks = []
    print(f"Loading chunks from {CHUNK_DIR}: {', '.join(json_files)}")
    for filename in json_files:
        path = os.path.join(CHUNK_DIR, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                chunks.extend(data)
            else:
                print(f"警告: {path} の形式がリストではありません。スキップします。")
        except FileNotFoundError:
            print(f"警告: {path} が見つかりません。スキップします。")
        except json.JSONDecodeError as e:
            print(f"警告: {path} の JSON パースに失敗しました: {e}")

    if not chunks:
        print("読み込める Chunk データがありません。")
        return

    # 4. EmbeddingGemma用フォーマット変換
    # 推奨フォーマット: "title: {Title} | text: {Body}"
    print("Formatting texts for EmbeddingGemma...")
    formatted_texts = []
    for chunk in chunks:
        # タイトルとして「法令名 + 条数 + 見出し」を設定
        title_part = f"{chunk['law_name']} {chunk['article_id']} {chunk['caption'] or ''}".strip()
        # 本文
        text_part = chunk['text']
        
        # フォーマット適用
        # titleが空の場合は "title: none | text: ..." とする仕様ですが、今回は必ず入る想定
        ft = f"title: {title_part} | text: {text_part}"
        formatted_texts.append(ft)

    # 5. ベクトル化 (Embedding)
    print("Starting embedding...")
    embeddings = model.encode(
        formatted_texts,
        batch_size=32,       # モデルが軽いのでバッチサイズを上げられます（8 -> 32）
        show_progress_bar=True,
        normalize_embeddings=True
    )

    # 6. Qdrantへの登録
    # client = QdrantClient("localhost", port=6333)
    client = QdrantClient(path="./qdrant_storage")
    
    # EmbeddingGemmaの次元数は 768 です
    vector_size = embeddings.shape[1] 
    print(f"Vector dimension: {vector_size}") # 768を確認

    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=vector_size,
            distance=models.Distance.COSINE
        )
    )

    print("Uploading to Qdrant...")
    points = []
    for i, chunk in enumerate(chunks):
        points.append(models.PointStruct(
            id=i,
            vector=embeddings[i].tolist(),
            payload={
                "law_name": chunk.get("law_name"),
                "article_id": chunk.get("article_id"),
                "caption": chunk.get("caption"),
                "text": chunk.get("text")
            }
        ))

    client.upload_points(collection_name=COLLECTION_NAME, points=points)
    print(f"完了: {len(points)} 件を '{COLLECTION_NAME}' に登録しました。")

if __name__ == "__main__":
    upsert_gemma()
