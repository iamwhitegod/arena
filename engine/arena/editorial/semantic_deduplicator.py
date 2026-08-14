"""
Semantic Deduplicator

Finds and clusters duplicate/similar ThoughtUnits using semantic embeddings.

Strategy:
- Generate embeddings for claim text (the core insight)
- Calculate cosine similarity between all pairs
- Cluster units with similarity >= threshold (default 0.85)
- Return clusters of similar units for variant selection

Why Claim Text?
- The claim is the core insight/message
- Most distinctive part of the ThoughtUnit
- Premises and resolutions can vary while claim stays same
"""

from typing import List, Dict, Tuple
from .thought_unit import ThoughtUnit
import numpy as np


class SemanticDeduplicator:
    """
    Finds duplicate/similar ThoughtUnits using semantic embeddings.

    Uses OpenAI text-embedding-3-small for efficient, accurate embeddings.
    Clusters units by cosine similarity to identify duplicates.
    """

    def __init__(self, api_key=None, model: str = "text-embedding-3-small", *, embedding=None):
        """
        Initialize semantic deduplicator

        Args:
            api_key: OpenAI API key (legacy, creates OpenAIEmbeddingModel internally)
            model: Embedding model (default: text-embedding-3-small)
            embedding: EmbeddingModel inference port (preferred)
        """
        if embedding is not None:
            self._embedding = embedding
        elif api_key is not None:
            from arena.providers.openai_adapter import OpenAIEmbeddingModel
            self._embedding = OpenAIEmbeddingModel(api_key=api_key, model=model)
        else:
            raise ValueError("Either embedding or api_key required")
        self.model = model
        self.metrics = {
            'api_calls': 0,
            'tokens_used': 0,
            'cost_usd': 0.0,
            'units_processed': 0,
            'clusters_found': 0,
            'duplicates_removed': 0
        }

    def deduplicate(
        self,
        thought_units: List[ThoughtUnit],
        similarity_threshold: float = 0.85,
        temporal_overlap_threshold: float = 0.5,
        verbose: bool = True
    ) -> Tuple[List[ThoughtUnit], List[List[ThoughtUnit]]]:
        """
        Deduplicate ThoughtUnits by semantic similarity AND temporal overlap.

        Args:
            thought_units: List of ThoughtUnit instances
            similarity_threshold: Minimum semantic similarity to cluster (0.0-1.0)
            temporal_overlap_threshold: Minimum temporal overlap ratio to cluster (0.0-1.0)
            verbose: Print progress

        Returns:
            Tuple of (unique_units, all_clusters)
            - unique_units: One representative from each cluster
            - all_clusters: All clusters found (for analysis)
        """
        if not thought_units:
            return [], []

        if verbose:
            print(f"\n📍 STEP: Semantic + Temporal Deduplication")
            print(f"   Input: {len(thought_units)} ThoughtUnits")
            print(f"   Semantic similarity threshold: {similarity_threshold:.2f}")
            print(f"   Temporal overlap threshold: {temporal_overlap_threshold:.2f}")

        # Step 1: Generate embeddings
        if verbose:
            print(f"   Generating embeddings...")

        embeddings = self._generate_embeddings(thought_units, verbose)

        # Step 2: Calculate similarity matrix
        if verbose:
            print(f"   Calculating similarity matrix...")

        similarity_matrix = self._calculate_similarity_matrix(embeddings)

        # Step 3: Calculate temporal overlap matrix
        if verbose:
            print(f"   Calculating temporal overlap matrix...")

        temporal_matrix = self._calculate_temporal_overlap_matrix(thought_units)

        # Step 4: Cluster similar units (semantic OR temporal)
        if verbose:
            print(f"   Clustering similar units...")

        clusters = self._cluster_similar_units(
            thought_units,
            similarity_matrix,
            temporal_matrix,
            similarity_threshold,
            temporal_overlap_threshold
        )

        # Step 5: Extract unique units (first in each cluster)
        unique_units = [cluster[0] for cluster in clusters]

        # Update metrics
        self.metrics['units_processed'] = len(thought_units)
        self.metrics['clusters_found'] = len(clusters)
        self.metrics['duplicates_removed'] = len(thought_units) - len(unique_units)

        if verbose:
            dedup_rate = (len(thought_units) - len(unique_units)) / len(thought_units) * 100
            print(f"   ✓ Found {len(clusters)} unique moments")
            print(f"   ✓ Removed {len(thought_units) - len(unique_units)} duplicates ({dedup_rate:.0f}% reduction)")

        return unique_units, clusters

    def _generate_embeddings(
        self,
        thought_units: List[ThoughtUnit],
        verbose: bool
    ) -> np.ndarray:
        """
        Generate embeddings for all ThoughtUnits.

        Args:
            thought_units: List of ThoughtUnit instances
            verbose: Print progress

        Returns:
            NumPy array of embeddings (shape: [num_units, embedding_dim])
        """
        # Extract claim texts
        texts = [unit.claim_text for unit in thought_units]

        # Generate embeddings (batched)
        response = self._embedding.embed(texts)

        # Track metrics
        self.metrics['api_calls'] += 1
        self.metrics['tokens_used'] += response.usage.total_tokens
        if response.usage.estimated_cost_usd is not None:
            self.metrics['cost_usd'] += float(response.usage.estimated_cost_usd)

        # Extract embeddings
        embeddings = np.array(response.embeddings)

        if verbose:
            print(f"      Generated {len(embeddings)} embeddings ({response.usage.total_tokens} tokens, ${self.metrics['cost_usd']:.4f})")

        return embeddings

    def _calculate_similarity_matrix(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Calculate pairwise cosine similarity matrix.

        Args:
            embeddings: NumPy array of embeddings

        Returns:
            Similarity matrix (shape: [num_units, num_units])
        """
        # Normalize embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / norms

        # Cosine similarity = dot product of normalized vectors
        similarity_matrix = np.dot(normalized, normalized.T)

        return similarity_matrix

    def _calculate_temporal_overlap_matrix(self, thought_units: List[ThoughtUnit]) -> np.ndarray:
        """
        Calculate pairwise temporal overlap matrix.

        Args:
            thought_units: List of ThoughtUnit instances

        Returns:
            Overlap matrix (shape: [num_units, num_units])
            Each cell contains the overlap ratio (0.0-1.0)
        """
        n = len(thought_units)
        overlap_matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                if i == j:
                    overlap_matrix[i][j] = 1.0  # Unit overlaps 100% with itself
                else:
                    overlap_matrix[i][j] = self._calculate_overlap_ratio(
                        thought_units[i],
                        thought_units[j]
                    )

        return overlap_matrix

    def _calculate_overlap_ratio(self, unit1: ThoughtUnit, unit2: ThoughtUnit) -> float:
        """
        Calculate temporal overlap ratio between two ThoughtUnits.

        Args:
            unit1: First ThoughtUnit
            unit2: Second ThoughtUnit

        Returns:
            Overlap ratio (0.0-1.0) = overlap_duration / shorter_unit_duration
        """
        # Get time ranges
        start1 = unit1.premise_start
        end1 = unit1.resolution_end
        start2 = unit2.premise_start
        end2 = unit2.resolution_end

        # Calculate overlap
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)
        overlap_duration = max(0, overlap_end - overlap_start)

        # Calculate ratio relative to shorter unit
        duration1 = end1 - start1
        duration2 = end2 - start2
        shorter_duration = min(duration1, duration2)

        if shorter_duration == 0:
            return 0.0

        return overlap_duration / shorter_duration

    def _cluster_similar_units(
        self,
        thought_units: List[ThoughtUnit],
        similarity_matrix: np.ndarray,
        temporal_matrix: np.ndarray,
        similarity_threshold: float,
        temporal_threshold: float
    ) -> List[List[ThoughtUnit]]:
        """
        Cluster ThoughtUnits by semantic similarity OR temporal overlap.

        Uses greedy clustering:
        - Start with first unit as cluster seed
        - Add all similar units (semantic OR temporal overlap)
        - Mark them as processed
        - Repeat with next unprocessed unit

        Args:
            thought_units: List of ThoughtUnit instances
            similarity_matrix: Pairwise semantic similarity matrix
            temporal_matrix: Pairwise temporal overlap matrix
            similarity_threshold: Minimum semantic similarity to cluster
            temporal_threshold: Minimum temporal overlap to cluster

        Returns:
            List of clusters, each containing similar ThoughtUnits
        """
        n = len(thought_units)
        processed = [False] * n
        clusters = []

        for i in range(n):
            if processed[i]:
                continue

            # Start new cluster with this unit
            cluster = [thought_units[i]]
            processed[i] = True

            # Find all similar units (semantic OR temporal)
            for j in range(i + 1, n):
                if processed[j]:
                    continue

                # Check if semantically similar OR temporally overlapping
                is_semantic_duplicate = similarity_matrix[i][j] >= similarity_threshold
                is_temporal_duplicate = temporal_matrix[i][j] >= temporal_threshold

                if is_semantic_duplicate or is_temporal_duplicate:
                    cluster.append(thought_units[j])
                    processed[j] = True

            clusters.append(cluster)

        return clusters

    def analyze_clusters(
        self,
        clusters: List[List[ThoughtUnit]],
        verbose: bool = True
    ) -> Dict:
        """
        Analyze clustering results.

        Args:
            clusters: List of clusters
            verbose: Print analysis

        Returns:
            Analysis dict with statistics
        """
        # Calculate statistics
        cluster_sizes = [len(cluster) for cluster in clusters]
        duplicates = [cluster for cluster in clusters if len(cluster) > 1]

        analysis = {
            'total_clusters': len(clusters),
            'singleton_clusters': sum(1 for size in cluster_sizes if size == 1),
            'duplicate_clusters': len(duplicates),
            'avg_cluster_size': np.mean(cluster_sizes),
            'max_cluster_size': max(cluster_sizes),
            'cluster_size_distribution': {
                '1': sum(1 for size in cluster_sizes if size == 1),
                '2': sum(1 for size in cluster_sizes if size == 2),
                '3+': sum(1 for size in cluster_sizes if size >= 3)
            }
        }

        if verbose:
            print(f"\n📊 Cluster Analysis:")
            print(f"   Total clusters: {analysis['total_clusters']}")
            print(f"   Singleton (unique): {analysis['singleton_clusters']}")
            print(f"   Duplicates: {analysis['duplicate_clusters']}")
            print(f"   Average cluster size: {analysis['avg_cluster_size']:.1f}")
            print(f"   Max cluster size: {analysis['max_cluster_size']}")
            print(f"   Distribution: 1={analysis['cluster_size_distribution']['1']}, " +
                  f"2={analysis['cluster_size_distribution']['2']}, " +
                  f"3+={analysis['cluster_size_distribution']['3+']}")

        return analysis

    def get_duplicate_pairs(
        self,
        clusters: List[List[ThoughtUnit]]
    ) -> List[Tuple[ThoughtUnit, ThoughtUnit]]:
        """
        Get all duplicate pairs for manual review.

        Args:
            clusters: List of clusters

        Returns:
            List of (unit1, unit2) pairs from same cluster
        """
        pairs = []

        for cluster in clusters:
            if len(cluster) < 2:
                continue

            # Get all pairs within cluster
            for i in range(len(cluster)):
                for j in range(i + 1, len(cluster)):
                    pairs.append((cluster[i], cluster[j]))

        return pairs
