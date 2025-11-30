import os
from dotenv import load_dotenv

load_dotenv()

# Collection Names
LEGAL_COLLECTION_NAME = "legal_rag_gemma"
IDEA_COLLECTION_NAME = "idea_frameworks"

# Models
EMBED_MODEL_ID = "google/embeddinggemma-300m"
CEREBRAS_MODEL_CHOICES = [
    "llama-3.3-70b",
    "gpt-oss-120b",
    "qwen-3-32b",
    "qwen-3-235b-a22b-instruct-2507",
    "zai-glm-4.6",
]

# API Keys & Endpoints
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
JINA_API_KEY = os.getenv("JINA_API_KEY")  # Optional
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")

# Qdrant settings (allow override via environment for Docker/docker-compose)
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# Analysis Steps (The Loop)
ANALYSIS_STEPS = {
    1: "STEEP分析",
    2: "5F分析",
    3: "リーンキャンバス",
    4: "オズボーンチェックリスト",
    5: "再リーンキャンバス",
    6: "ペルソナ",
    7: "課題仮説構築",
    8: "インタビュー項目作成",
    9: "カスタマージャーニー",
    10: "総合要点まとめ"
}
