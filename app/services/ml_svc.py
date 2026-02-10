from __future__ import annotations

import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer


class TopicModellingService:
    """Topic extraction service for abstracts and query seeds."""

    def perform_lda(self, documents: list[str], n_topics: int = 2) -> list[str]:
        """Run LDA to derive compact topic descriptors."""
        if not documents:
            return []
        vectorizer = CountVectorizer(max_df=0.95, min_df=2, stop_words="english")
        matrix = vectorizer.fit_transform(documents)
        lda = LatentDirichletAllocation(n_components=n_topics, random_state=0)
        lda.fit(matrix)
        feature_names = vectorizer.get_feature_names_out()
        return [" ".join([feature_names[index] for index in topic.argsort()[:-6:-1]]) for topic in lda.components_]

    def recommend_top2vec_seeds(self, documents: list[str]) -> list[str]:
        """Recommend seed keywords based on term-frequency ranking."""
        if not documents:
            return []
        vectorizer = CountVectorizer(stop_words="english", max_features=20)
        matrix = vectorizer.fit_transform(documents)
        scores = np.asarray(matrix.sum(axis=0)).ravel()
        terms = vectorizer.get_feature_names_out()
        ranked = sorted(zip(terms, scores), key=lambda term_score: term_score[1], reverse=True)
        return [term for term, _ in ranked[:5]]


class ClusterService:
    """Narrative clustering for grouped signal presentation."""

    def cluster_signals(self, signals: list[dict]) -> list[dict]:
        """Cluster signals into narrative groups."""
        if len(signals) < 3:
            return []

        texts = [f"{signal['title']} {signal['summary']}" for signal in signals]
        vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)
        matrix = vectorizer.fit_transform(texts)

        cluster_count = max(2, len(signals) // 5)
        kmeans = MiniBatchKMeans(n_clusters=cluster_count, random_state=42).fit(matrix)

        grouped: dict[str, dict] = {}
        for index, label in enumerate(kmeans.labels_):
            cluster_id = str(label)
            grouped.setdefault(cluster_id, {"signals": []})["signals"].append(signals[index])

        order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]
        terms = vectorizer.get_feature_names_out()

        results: list[dict] = []
        for cluster_id, cluster_data in grouped.items():
            centroid_index = int(cluster_id)
            top_terms = [terms[index] for index in order_centroids[centroid_index, :3]]
            results.append(
                {
                    "title": f"Narrative: {', '.join(top_terms).title()}",
                    "count": len(cluster_data["signals"]),
                    "signals": cluster_data["signals"],
                    "keywords": top_terms,
                }
            )
        return results
