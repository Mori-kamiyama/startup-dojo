import torch
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import streamlit as st
from config import (
    LEGAL_COLLECTION_NAME, 
    IDEA_COLLECTION_NAME, 
    EMBED_MODEL_ID, 
    QDRANT_HOST, 
    QDRANT_PORT
)
from utils.prompts import IDEA_SYSTEM_PROMPT_TEMPLATE, LEGAL_SYSTEM_PROMPT_TEMPLATE

@st.cache_resource
def get_retrieval_resources():
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"

    model = SentenceTransformer(EMBED_MODEL_ID, device=device, trust_remote_code=True)
    client = QdrantClient(QDRANT_HOST, port=QDRANT_PORT)
    return model, client

def build_system_prompt(user_query, mode_label, current_phase, model, qdrant_client, cerebras_model_id, top_k=3):
    is_idea_mode = "Idea" in mode_label
    
    if is_idea_mode:
        collection = IDEA_COLLECTION_NAME
        sys_prompt_base = IDEA_SYSTEM_PROMPT_TEMPLATE.format(
            model_id=cerebras_model_id,
            current_phase=current_phase
        )
        formatted_query = f"task: search framework | query: {user_query}"
    else:
        collection = LEGAL_COLLECTION_NAME
        sys_prompt_base = LEGAL_SYSTEM_PROMPT_TEMPLATE.format(model_id=cerebras_model_id)
        formatted_query = f"task: search result | query: {user_query}"

    # Search
    query_vector = model.encode(formatted_query, normalize_embeddings=True)
    try:
        resp = qdrant_client.query_points(
            collection_name=collection,
            query=query_vector,
            limit=top_k,
        )
        results = resp.points
    except Exception:
        results = []

    # Context構築
    context_blocks = []
    for res in results:
        payload = res.payload
        title = payload.get("title") or f"{payload.get('law_name')} {payload.get('article_id')}"
        text = payload.get("text", "")
        context_blocks.append(f"📜【参照データ: {title}】\n{text}")
    
    context_str = "\n\n".join(context_blocks)
    
    final_system_prompt = f"""
    {sys_prompt_base}

    === 以下の知識を脳にインストールして回答せよ ===
    {context_str}
    """
    
    return final_system_prompt, results
