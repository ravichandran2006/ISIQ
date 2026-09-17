import numpy as np
from typing import List, Dict, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class SemanticVectorEngine:
    """
    Lightweight, deterministic semantic embedding and vector similarity engine.
    Ensures sub-millisecond retrieval without heavy cloud API dependencies or network latency.
    """

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            max_features=5000,
            sublinear_tf=True,
            stop_words="english"
        )
        self.doc_ids: List[int] = []
        self.doc_vectors = None
        self.is_fitted = False

    def build_index(self, documents: List[Dict[str, Any]]):
        """
        Builds the vector corpus from standard title, scope, ICS, and committee metadata.
        """
        if not documents:
            return

        self.doc_ids = [doc["id"] for doc in documents]
        corpus = []

        for doc in documents:
            # Create rich dense representation
            text_rep = f"{doc.get('standard_number', '')} {doc.get('title', '')} {doc.get('domain', '')} {doc.get('committee_code', '')} {doc.get('scope', '')}"
            corpus.append(text_rep)

        self.doc_vectors = self.vectorizer.fit_transform(corpus)
        self.is_fitted = True

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        if not self.is_fitted or self.doc_vectors is None:
            return []

        query_vec = self.vectorizer.transform([query])
        sim_scores = cosine_similarity(query_vec, self.doc_vectors).flatten()

        top_indices = np.argsort(sim_scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            score = float(sim_scores[idx])
            if score > 0.01:
                results.append((self.doc_ids[idx], score))

        return results
