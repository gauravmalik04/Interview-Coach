import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.utils import embedding_functions

from backend.config import settings

logger = logging.getLogger("ai_interview.embedding_service")

class EmbeddingService:
    """Service to handle vector embeddings, hybrid chunking, and ChromaDB retrieval."""

    def __init__(self):
        self._client: Optional[chromadb.ClientAPI] = None
        self._collection = None
        self._embedding_fn = None

    def _ensure_initialized(self):
        """Lazy initialization of ChromaDB persistent client and collection."""
        if self._collection is not None:
            return

        try:
            logger.info(f"Initializing ChromaDB at persist path: {settings.CHROMA_PERSIST_PATH}")
            self._client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_PATH)
            
            # Using sentence-transformers embedding function
            self._embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.EMBEDDING_MODEL_NAME
            )
            
            self._collection = self._client.get_or_create_collection(
                name="interview_evaluations",
                embedding_function=self._embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB evaluation collection initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")
            raise

    def store_evaluation_chunks(
        self,
        candidate_id: str,
        interview_id: str,
        report_data: Dict[str, Any],
        date_str: Optional[str] = None
    ) -> bool:
        """
        Implements Hybrid Chunking strategy:
        - Chunk 0: Overall summary and score
        - Chunks 1-7: One chunk per evaluation dimension (score + rationale)
        - Chunk 8: Recommended focus areas and improvement plan
        """
        self._ensure_initialized()

        if not date_str:
            date_str = datetime.now(timezone.utc).isoformat()

        chunks: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        ids: List[str] = []

        # 1. Summary Chunk
        overall_score = report_data.get("overall_score", 0.0)
        detailed_feedback = report_data.get("detailed_feedback", "")
        summary_text = (
            f"Interview Summary on {report_data.get('topic', 'Technical Interview')} ({date_str}). "
            f"Overall Score: {overall_score}/4.0. "
            f"Evaluation Feedback: {detailed_feedback}"
        )
        chunks.append(summary_text)
        metadatas.append({
            "candidate_id": candidate_id,
            "interview_id": interview_id,
            "date": date_str,
            "chunk_type": "summary",
            "metric_name": "overall",
            "score": float(overall_score)
        })
        ids.append(f"{interview_id}_chunk_summary")

        # 2-8. Discrete Evaluation Metric Chunks
        dsa_metrics = report_data.get("dsa_metrics", {})
        topic_name = report_data.get("topic", "Technical DSA")
        if dsa_metrics:
            for metric_key, m_info in dsa_metrics.items():
                m_name = m_info.get("name", metric_key)
                m_score = m_info.get("score", 2.5)
                m_rationale = m_info.get("rationale", "")
                m_evidence = m_info.get("evidence_quote", "")
                m_tip = m_info.get("growth_tip", "")

                metric_doc = (
                    f"Interview Assessment ({topic_name} - {date_str})\n"
                    f"Evaluation Metric: {m_name}\n"
                    f"Candidate Score: {m_score} / 4.0\n"
                    f"Evaluator Assessment: {m_rationale}\n"
                    f"Candidate Evidence: {m_evidence}\n"
                    f"Targeted Growth Guidance: {m_tip}"
                )
                chunks.append(metric_doc)
                metadatas.append({
                    "candidate_id": candidate_id,
                    "interview_id": interview_id,
                    "topic": topic_name,
                    "date": date_str,
                    "chunk_type": "metric",
                    "metric_name": metric_key,
                    "score": float(m_score)
                })
                ids.append(f"{interview_id}_metric_{metric_key}")
        else:
            dimension_scores = report_data.get("dimension_scores", {})
            dimension_rationales = report_data.get("dimension_rationales", {})
            for dim_name, score in dimension_scores.items():
                rationale = dimension_rationales.get(dim_name, "Evaluated according to standard rubric.")
                dim_text = (
                    f"Evaluation Dimension: {dim_name}. "
                    f"Score: {score}/4.0. "
                    f"Assessment & Rationale: {rationale}"
                )
                chunks.append(dim_text)
                metadatas.append({
                    "candidate_id": candidate_id,
                    "interview_id": interview_id,
                    "topic": topic_name,
                    "date": date_str,
                    "chunk_type": f"dimension_{dim_name}",
                    "metric_name": dim_name,
                    "score": float(score)
                })
                ids.append(f"{interview_id}_chunk_dim_{dim_name}")

        # 9. Focus Areas and Action Plan Chunk
        strengths = ", ".join(report_data.get("strengths", []))
        improvements = ", ".join(report_data.get("improvement_areas", []))
        focus_areas = ", ".join(report_data.get("recommended_focus_areas", []))
        
        action_text = (
            f"Candidate Strengths: {strengths}. "
            f"Areas for Improvement: {improvements}. "
            f"Recommended Focus Areas: {focus_areas}."
        )
        chunks.append(action_text)
        metadatas.append({
            "candidate_id": candidate_id,
            "interview_id": interview_id,
            "topic": topic_name,
            "date": date_str,
            "chunk_type": "focus_areas",
            "metric_name": "recommendations",
            "score": 0.0
        })
        ids.append(f"{interview_id}_chunk_focus_areas")

        try:
            self._collection.upsert(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Successfully stored {len(chunks)} evaluation chunks in ChromaDB for interview {interview_id}.")
            return True
        except Exception as e:
            logger.error(f"Failed to upsert chunks to ChromaDB: {e}")
            return False

    def query_candidate_history(
        self,
        candidate_id: str,
        query_text: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Query past interview evaluations for a candidate using semantic similarity and candidate_id filter."""
        self._ensure_initialized()

        try:
            results = self._collection.query(
                query_texts=[query_text],
                where={"candidate_id": candidate_id},
                n_results=n_results
            )

            formatted_results = []
            if results and results.get("documents") and len(results["documents"]) > 0:
                docs = results["documents"][0]
                metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
                dists = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

                for doc, meta, dist in zip(docs, metas, dists):
                    formatted_results.append({
                        "text": doc,
                        "metadata": meta,
                        "distance": dist
                    })

            return formatted_results
        except Exception as e:
            logger.error(f"Error querying candidate history in ChromaDB: {e}")
            return []

    def query_metric_history(
        self,
        candidate_id: str,
        metric_name: Optional[str] = None,
        query_text: Optional[str] = None,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Query evaluation chunks for a candidate, optionally filtered by metric_name."""
        self._ensure_initialized()

        try:
            where_clause = {"candidate_id": candidate_id}
            if metric_name:
                where_clause = {
                    "$and": [
                        {"candidate_id": candidate_id},
                        {"metric_name": metric_name}
                    ]
                }
            search_query = query_text or (f"Performance on {metric_name}" if metric_name else "Evaluation summary and performance")
            results = self._collection.query(
                query_texts=[search_query],
                where=where_clause,
                n_results=n_results
            )

            formatted_results = []
            if results and results.get("documents") and len(results["documents"]) > 0:
                docs = results["documents"][0]
                metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
                dists = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

                for doc, meta, dist in zip(docs, metas, dists):
                    formatted_results.append({
                        "text": doc,
                        "metadata": meta,
                        "distance": dist
                    })

            return formatted_results
        except Exception as e:
            logger.error(f"Error querying metric history in ChromaDB: {e}")
            return []

# Global singleton embedding service
embedding_service = EmbeddingService()
