import torch
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# --- 設定 ---
COLLECTION_NAME = "legal_rag_gemma"
MODEL_ID = "google/embeddinggemma-300m"


def search_law_gemma(user_query):
    # 1. モデルロード
    device = "cuda" if torch.cuda.is_available() else "cpu"
    # ※ 実際のアプリではモデルのロードは起動時の1回だけにします
    model = SentenceTransformer(MODEL_ID, device=device, trust_remote_code=True)
    client = QdrantClient("localhost", port=6333)

    # 2. EmbeddingGemma用クエリフォーマット
    # task: search result | query: {content}
    formatted_query = f"task: search result | query: {user_query}"

    print(f"\n--- Search Query ---\n{formatted_query}\n--------------------")

    # 3. ベクトル化
    query_vector = model.encode(formatted_query, normalize_embeddings=True)

    # 4. 検索（query_points API を使用）
    resp = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=3,
    )
    results = resp.points

    # 5. 結果表示
    print(f"\n質問: {user_query}")
    print("=" * 30)
    for res in results:
        payload = res.payload
        print(f"Score: {res.score:.4f}")
        # タイトルを見やすく表示
        title = f\"{payload['law_name']} {payload['article_id']} {payload['caption'] or ''}\"
        print(f\"【{title}】\")
        print(f\"{payload['text'][:100]}...\")
        print(\"-\" * 20)

if __name__ == "__main__":
    # テスト
    questions = [
        "社員をクビにしたい場合、いつまでに言えばいい？",
        "給料の支払いで通貨以外を使ってもいいの？"
    ]
    
    for q in questions:
        search_law_gemma(q)
