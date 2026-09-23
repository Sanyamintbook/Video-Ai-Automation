import os
import math
import json
import pickle
from typing import List
import httpx
from loguru import logger
from app.config.settings import get_settings


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


class LocalVectorStore:
    def __init__(self, dimension: int = 768):
        settings = get_settings()
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_embedding_model or "nomic-embed-text"
        self.dimension = None
        self.chunks: List[str] = []
        self.embeddings: List[List[float]] = []
        self.faiss_index = None

    def _ensure_model_exists(self) -> None:
        with httpx.Client(timeout=get_settings().ollama_embedding_timeout_seconds) as client:
            try:
                response = client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": self.model, "stream": False}
                )
                response.raise_for_status()
            except Exception as exc:
                logger.warning(f"Could not auto-pull model '{self.model}': {exc}")

    def _get_embedding(self, text: str) -> List[float]:
        with httpx.Client(timeout=get_settings().ollama_embedding_timeout_seconds) as client:
            try:
                response = client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text}
                )
                if response.status_code == 404:
                    self._ensure_model_exists()
                    response = client.post(
                        f"{self.base_url}/api/embeddings",
                        json={"model": self.model, "prompt": text}
                    )
                response.raise_for_status()
                data = response.json()
                return data["embedding"]
            except Exception as exc:
                logger.error(f"Failed to connect to Ollama for embeddings at {self.base_url}: {exc}")
                raise

    def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        with httpx.Client(timeout=get_settings().ollama_embedding_timeout_seconds) as client:
            try:
                all_embeddings = []
                batch_size = 50
                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i:i + batch_size]
                    response = client.post(
                        f"{self.base_url}/api/embed",
                        json={"model": self.model, "input": batch_texts}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if "embeddings" in data:
                            all_embeddings.extend(data["embeddings"])
                        else:
                            raise Exception("No embeddings in response")
                    else:
                        raise Exception(f"HTTP {response.status_code}")
                return all_embeddings
            except Exception:
                pass

        # Fallback sequential
        embeddings = []
        with httpx.Client(timeout=get_settings().ollama_embedding_timeout_seconds) as client:
            for text in texts:
                response = client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text}
                )
                response.raise_for_status()
                embeddings.append(response.json()["embedding"])
        return embeddings

    def add_documents(self, documents: List[str]) -> None:
        if not documents:
            return
        embeddings = self._get_embeddings_batch(documents)
        self.chunks.extend(documents)
        self.embeddings.extend(embeddings)
        
        # Try FAISS if available
        try:
            import faiss
            import numpy as np
            embeddings_np = np.array(self.embeddings).astype("float32")
            self.dimension = embeddings_np.shape[1]
            self.faiss_index = faiss.IndexFlatL2(self.dimension)
            self.faiss_index.add(embeddings_np)
        except Exception:
            self.faiss_index = None

        logger.info(f"Added {len(documents)} chunks to local vector store.")

    def similarity_search(self, query: str, top_k: int = 3) -> List[str]:
        if not self.chunks:
            return []
            
        query_vector = self._get_embedding(query)
        
        # Method 1: FAISS
        if self.faiss_index:
            try:
                import numpy as np
                query_vector_np = np.array([query_vector]).astype("float32")
                distances, indices = self.faiss_index.search(query_vector_np, min(top_k, len(self.chunks)))
                results = []
                for idx in indices[0]:
                    if idx != -1 and idx < len(self.chunks):
                        results.append(self.chunks[idx])
                return results
            except Exception:
                pass

        # Method 2: Pure Python Cosine Similarity
        scored = []
        for doc_text, doc_emb in zip(self.chunks, self.embeddings):
            score = cosine_similarity(query_vector, doc_emb)
            scored.append((score, doc_text))
            
        scored.sort(key=lambda x: x[0], reverse=True)
        return [text for score, text in scored[:top_k]]

    def save(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        data = {
            "chunks": self.chunks,
            "embeddings": self.embeddings
        }
        with open(os.path.join(directory, "store.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)
        logger.info(f"Saved local vector store to {directory}")

    def load(self, directory: str) -> None:
        store_path = os.path.join(directory, "store.json")
        if not os.path.exists(store_path):
            raise FileNotFoundError(f"Vector store not found in {directory}")
            
        with open(store_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        self.chunks = data.get("chunks", [])
        self.embeddings = data.get("embeddings", [])
        logger.info(f"Loaded {len(self.chunks)} chunks from local vector store.")
