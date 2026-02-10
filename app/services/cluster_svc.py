from __future__ import annotations

from typing import Any

from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer


class ClusterService:
    """Cluster incoming signals into interpretable narrative groups."""

    def cluster_signals(self, signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Build TF-IDF vectors and group signals via MiniBatch K-Means."""
        if len(signals) < 3:
            return []

        texts = [f"{signal.get('title', '')} {signal.get('summary', '')}".strip() for signal in signals]
        vectoriser = TfidfVectorizer(stop_words="english", max_features=1000)
        matrix = vectoriser.fit_transform(texts)

        cluster_count = max(2, len(signals) // 5)
        kmeans = MiniBatchKMeans(n_clusters=cluster_count, random_state=42).fit(matrix)

        grouped_clusters: dict[str, dict[str, Any]] = {}
        for index, label in enumerate(kmeans.labels_):
            cluster_id = str(label)
            grouped_clusters.setdefault(cluster_id, {"signals": []})["signals"].append(signals[index])

        terms = vectoriser.get_feature_names_out()
        centroid_order = kmeans.cluster_centers_.argsort()[:, ::-1]

        results: list[dict[str, Any]] = []
        for cluster_id, cluster_payload in grouped_clusters.items():
            centroid_index = int(cluster_id)
            top_terms = [terms[index] for index in centroid_order[centroid_index, :3]]
            results.append(
                {
                    "id": cluster_id,
                    "title": f"Narrative: {', '.join(top_terms).title()}",
                    "count": len(cluster_payload["signals"]),
                    "signals": cluster_payload["signals"],
                    "keywords": top_terms,
                }
            )

        return sorted(results, key=lambda cluster: cluster["count"], reverse=True)
