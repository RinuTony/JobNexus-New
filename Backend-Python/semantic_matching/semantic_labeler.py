# semantic_labeler.py
import json
import numpy as np
from embeddings import Embedder
from config import EMBEDDING_MODEL, SIMILARITY_THRESHOLD

class SemanticLabeler:
    def __init__(self, prototype_path: str, model_name: str = EMBEDDING_MODEL):
        self.embedder = Embedder(model_name)
        with open(prototype_path, "r", encoding="utf-8") as f:
            self.prototypes = json.load(f)
        # Precompute prototype embeddings and centroid per category
        self.categories = list(self.prototypes.keys())
        all_protos = []
        self.proto_map = []  # (category_index)
        for idx, cat in enumerate(self.categories):
            examples = self.prototypes[cat]
            all_protos.extend(examples)
            self.proto_map.extend([idx] * len(examples))
        proto_embs = self.embedder.embed_sentences(all_protos)
        # compute centroid per category
        self.centroids = []
        for idx, cat in enumerate(self.categories):
            mask = [i for i, m in enumerate(self.proto_map) if m == idx]
            centroid = proto_embs[mask].mean(axis=0)
            # normalize
            centroid = centroid / (np.linalg.norm(centroid) + 1e-9)
            self.centroids.append(centroid)
        self.centroids = np.vstack(self.centroids)  # shape (C, d)

    def label_sentences(self, sentences):
        """
        sentences: list[str]
        returns: list of dicts: {"sentence": s, "category": cat or "unknown", "score": float}
        """
        s_embs = self.embedder.embed_sentences(sentences)  # (n,d)
        # cosine similarity with each centroid
        sims = s_embs.dot(self.centroids.T)  # (n, C)
        labels = []
        for i, s in enumerate(sentences):
            best_idx = int(np.argmax(sims[i]))
            score = float(sims[i, best_idx])
            cat = self.categories[best_idx] if score >= SIMILARITY_THRESHOLD else "unknown"
            labels.append({"sentence": s, "category": cat, "score": score})
        return labels
