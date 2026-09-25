import os
import json
import hashlib
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer

try:
    from fastembed import TextEmbedding
    FASTEMBED_AVAILABLE = True
except ImportError:
    FASTEMBED_AVAILABLE = False


class SemanticVectorEngine:
    """
    High-performance BGE dense semantic embedding and vector similarity engine.
    Uses BAAI/bge-small-en-v1.5 dense embeddings with persistent disk caching
    and TF-IDF hybrid lexical retrieval.
    """

    MODEL_NAME = "BAAI/bge-small-en-v1.5"

    def __init__(self, cache_dir: str = "./data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.doc_ids: List[int] = []
        self.doc_vectors: Optional[np.ndarray] = None
        self.corpus_texts: List[str] = []
        self.is_fitted: bool = False
        self._embedder = None
        self.tfidf_vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
        self._init_model()

    def _init_model(self):
        if FASTEMBED_AVAILABLE:
            try:
                os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
                self._embedder = TextEmbedding(model_name=self.MODEL_NAME)
            except Exception as e:
                print(f"[SEMANTIC VECTOR ENGINE ERROR] Failed to load {self.MODEL_NAME}: {e}")
                self._embedder = None

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Embeds a list of texts into normalized dense BGE vectors (384-dim).
        """
        if not texts:
            return np.empty((0, 384), dtype=np.float32)

        if self._embedder is not None:
            try:
                raw_embs = list(self._embedder.embed(texts))
                vecs = np.array(raw_embs, dtype=np.float32)
                norms = np.linalg.norm(vecs, axis=1, keepdims=True)
                norms[norms == 0] = 1e-10
                return vecs / norms
            except Exception as e:
                print(f"[EMBED ERROR] fastembed embedding failed: {e}")

        # Fallback pseudo-dense vectors
        return np.zeros((len(texts), 384), dtype=np.float32)

    def embed_single(self, text: str) -> np.ndarray:
        vecs = self.embed_texts([text])
        return vecs[0] if len(vecs) > 0 else np.zeros(384, dtype=np.float32)

    def _get_cache_hash(self, documents: List[Dict[str, Any]]) -> str:
        raw_repr = "".join(f"{d.get('id')}:{d.get('standard_number')}:{d.get('title')}" for d in documents)
        return hashlib.md5(raw_repr.encode("utf-8")).hexdigest()

    def build_index(self, documents: List[Dict[str, Any]], force_refresh: bool = False):
        """
        Builds the vector corpus from standard title, scope, domain, ICS, and committee metadata.
        Uses on-disk cache if documents haven't changed.
        """
        if not documents:
            return

        current_ids = [doc["id"] for doc in documents]

        # Check in-memory fast return
        if self.is_fitted and self.doc_ids == current_ids and not force_refresh:
            return

        corpus = []
        for doc in documents:
            text_rep = f"Standard {doc.get('standard_number', '')}: {doc.get('title', '')}. Domain: {doc.get('domain', '')}. Scope: {doc.get('scope', '')}"
            corpus.append(text_rep)

        self.corpus_texts = corpus
        self.doc_ids = current_ids

        # Build TF-IDF Lexical Index for ultra-fast hybrid token matching
        try:
            self.tfidf_vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", max_features=5000)
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(corpus)
        except Exception:
            self.tfidf_vectorizer = None
            self.tfidf_matrix = None

        # Check persistent on-disk cache for BGE dense vectors
        cache_hash = self._get_cache_hash(documents)
        vec_cache_file = os.path.join(self.cache_dir, f"bge_vectors_{cache_hash}.npy")
        meta_cache_file = os.path.join(self.cache_dir, f"bge_meta_{cache_hash}.json")

        if not force_refresh and os.path.exists(vec_cache_file) and os.path.exists(meta_cache_file):
            try:
                self.doc_vectors = np.load(vec_cache_file)
                self.is_fitted = True
                return
            except Exception:
                pass

        # Compute dense embeddings
        self.doc_vectors = self.embed_texts(corpus)
        self.is_fitted = True

        # Save to disk
        try:
            np.save(vec_cache_file, self.doc_vectors)
            with open(meta_cache_file, "w", encoding="utf-8") as f:
                json.dump({"doc_ids": self.doc_ids, "hash": cache_hash}, f)
        except Exception as e:
            print(f"[CACHE WRITE WARNING] Could not persist vector cache: {e}")

    def search(self, query: str, top_k: int = 15, min_threshold: float = 0.35) -> List[Tuple[int, float]]:
        """
        Computes hybrid similarity (BGE dense cosine + TF-IDF lexical).
        Returns (doc_id, score) pairs sorted descending.
        """
        if not self.is_fitted or len(self.doc_ids) == 0:
            return []

        doc_count = len(self.doc_ids)
        dense_scores = np.zeros(doc_count, dtype=np.float32)

        # 1. Dense Semantic Cosine Similarity
        if self.doc_vectors is not None:
            query_vec = self.embed_single(query)
            if not np.all(query_vec == 0):
                dense_scores = np.dot(self.doc_vectors, query_vec).flatten()

        # 2. TF-IDF Lexical Similarity
        tfidf_scores = np.zeros(doc_count, dtype=np.float32)
        if self.tfidf_vectorizer is not None and self.tfidf_matrix is not None:
            try:
                q_vec = self.tfidf_vectorizer.transform([query])
                raw_tf = (self.tfidf_matrix * q_vec.T).toarray().flatten()
                tfidf_scores = raw_tf.astype(np.float32)
            except Exception:
                pass

        # 3. Hybrid Blending
        # Dense is weighted 0.70, Lexical is weighted 0.30; if dense is all 0, lexical takes full weight
        has_dense = not np.all(dense_scores == 0)
        if has_dense:
            blended_scores = (0.72 * dense_scores) + (0.28 * tfidf_scores)
            # Give boost if exact term match occurs
            for idx in range(doc_count):
                if tfidf_scores[idx] > 0.4:
                    blended_scores[idx] = max(blended_scores[idx], dense_scores[idx] + 0.1)
        else:
            blended_scores = tfidf_scores

        top_indices = np.argsort(blended_scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            score = float(blended_scores[idx])
            if score >= min_threshold:
                results.append((self.doc_ids[idx], score))

        return results


# Global singleton instance
_GLOBAL_VECTOR_ENGINE: Optional[SemanticVectorEngine] = None

def get_semantic_vector_engine() -> SemanticVectorEngine:
    global _GLOBAL_VECTOR_ENGINE
    if _GLOBAL_VECTOR_ENGINE is None:
        _GLOBAL_VECTOR_ENGINE = SemanticVectorEngine()
    return _GLOBAL_VECTOR_ENGINE
