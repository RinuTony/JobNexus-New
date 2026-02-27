# core/embeddings.py
from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np

class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
    def encode(self, text: str) -> np.ndarray:
        """Encode single text to embedding"""
        return self.model.encode(text, normalize_embeddings=True)
    
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """Encode batch of texts to embeddings"""
        return self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Alias for encode (for compatibility)"""
        return self.encode(text)