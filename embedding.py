import json
import torch
from sentence_transformers import SentenceTransformer
import numpy as np

def generate_embeddings(input_json_path, output_json_path, model_id):
    """
    指定されたモデルを使ってテキストをベクトル化し、元のJSONに結合して保存する。
    """
    
    # 1. デバイスの設定 (MacBookではMPS(Apple Silicon GPU)またはCPUを使用)
    if torch.backends.mps.is_available():
        device = "mps"
        print("Using Apple Silicon GPU (MPS)")
    elif torch.cuda.is_available():
        device = "cuda"
        print("Using CUDA GPU")
    else:
        device = "cpu"
        print("Using CPU")

    # 2. データの読み込み
    try:
        with open(input_json_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        print(f"Loaded {len(chunks)} chunks from {input_json_path}")
    except FileNotFoundError:
        print(f"Error: {input_json_path} が見つかりません。")
        return

    # 3. モデルのロード
    print(f"Loading model: {model_id} ...")
    try:
        model = SentenceTransformer(model_id, device=device, trust_remote_code=True)
    except Exception as e:
        print(f"Model load error: {e}")
        print("Hugging FaceのモデルIDが正しいか確認してください。")
        return

    # 4. ベクトル化対象のテキストを抽出
    texts = [chunk["combined_text"] for chunk in chunks]

    # 5. Embeddingの実行
    print("Starting embedding process...")
    
    # MacBook用にバッチサイズを調整
    batch_size = 4 if device == "mps" else 8
    
    embeddings = model.encode(
        texts, 
        batch_size=batch_size, 
        show_progress_bar=True, 
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    # 6. 結果を結合
    print("Saving results...")
    for i, chunk in enumerate(chunks):
        chunk["vector"] = embeddings[i].tolist()

    # 7. 保存
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print(f"Done! Vectors saved to {output_json_path}")
    print(f"Vector dimensions: {embeddings.shape[1]}")

# --- 設定と実行 ---
if __name__ == "__main__":
    # 処理するファイルリスト
    files_to_process = [
        ("labor_standards_act_chunks.json", "labor_standards_act_vectors.json"),
        ("specific_commercial_transaction_act_chunks.json", "specific_commercial_transaction_act_vectors.json"),
        ("companies_act_chunks.json", "companies_act_vectors.json"),
    ]
    
    MODEL_ID = "sbintuitions/sarashina-embedding-v2-1b"  # 日本語対応の軽量モデル
    
    for input_file, output_file in files_to_process:
        print(f"\n=== Processing {input_file} ===")
        generate_embeddings(input_file, output_file, MODEL_ID)