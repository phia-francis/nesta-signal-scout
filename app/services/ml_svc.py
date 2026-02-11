from __future__ import annotations

import asyncio

import numpy as np
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer


class TopicModellingService:
    """Topic extraction service for abstracts and query seeds."""

    async def perform_lda(self, documents: list[str], n_topics: int = 2) -> list[str]:
        """Run LDA in a worker thread to avoid blocking the event loop."""
        return await asyncio.to_thread(self._run_lda_sync, documents, n_topics)

    def _run_lda_sync(self, documents: list[str], n_topics: int = 2) -> list[str]:
        if not documents:
            return []
        vectoriser = CountVectorizer(max_df=0.95, min_df=2, stop_words="english")
        matrix = vectoriser.fit_transform(documents)
        lda = LatentDirichletAllocation(n_components=n_topics, random_state=0)
        lda.fit(matrix)
        feature_names = vectoriser.get_feature_names_out()
        return [
            " ".join([feature_names[index] for index in topic.argsort()[:-6:-1]])
            for topic in lda.components_
        ]

    async def recommend_top2vec_seeds(self, documents: list[str]) -> list[str]:
        """Recommend term-frequency seed keywords in a worker thread."""
        return await asyncio.to_thread(self._recommend_top2vec_seeds_sync, documents)

    def _recommend_top2vec_seeds_sync(self, documents: list[str]) -> list[str]:
        if not documents:
            return []
        vectoriser = CountVectorizer(stop_words="english", max_features=20)
        matrix = vectoriser.fit_transform(documents)
        scores = np.asarray(matrix.sum(axis=0)).ravel()
        terms = vectoriser.get_feature_names_out()
        ranked = sorted(zip(terms, scores), key=lambda term_score: term_score[1], reverse=True)
        return [term for term, _ in ranked[:5]]
