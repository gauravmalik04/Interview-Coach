import json
import logging
import re
from typing import Dict, Any, List, Optional, Union
import anyio
from huggingface_hub import InferenceClient

from backend.config import settings
from backend.models.interview import DEFAULT_MEMORY_STATE
from backend.services.question_loader import QuestionItem

logger = logging.getLogger("ai_interview.state_extractor")

EXTRACTION_SYSTEM_PROMPT = """You are a low-latency, real-time DSA Technical Interview Memory Extractor.
Your sole job is to analyze the candidate's latest reply in the context of the technical problem, extract structured algorithmic observations, and update the session's cumulative memory state.

OUTPUT FORMAT:
You MUST respond with a single, valid JSON object ONLY. Do NOT output any markdown backticks, explanations, or commentary.
Schema:
{
  "data_structures_used": ["list", "of", "data", "structures"],
  "claimed_time_complexity": "e.g. O(N) or O(N^2) or null",
  "claimed_space_complexity": "e.g. O(1) or O(N) or null",
  "identified_edge_cases": ["list", "of", "edge", "cases", "handled"],
  "open_weaknesses": ["list", "of", "unresolved", "issues", "or", "inefficiencies"],
  "key_algorithmic_approach": "concise description of candidate approach"
}

GUIDELINES:
1. Merge new facts with the existing memory state without discarding previously verified facts unless the candidate explicitly revised their approach.
2. Identify any mentioned or implemented data structures (e.g. Hash Map, Monotonic Stack, Two Pointers, Heap, Trie, DP Array).
3. Extract explicitly claimed or inferred Big-O Time & Space complexities.
4. Note edge cases the candidate discussed (e.g. empty input, duplicates, negative numbers, overflow).
5. Record open weaknesses or unaddressed issues (e.g. brute-force quadratic complexity, unhandled edge cases, memory overhead).
6. Be concise, accurate, and output strictly JSON.
"""

KNOWN_DATA_STRUCTURES = {
    "hash map": ["hash map", "hashmap", "dictionary", "dict", "hash table", "hashtable"],
    "hash set": ["hash set", "hashset", "set()", "seen set", "lookup set"],
    "array / list": ["array", "list", "vector"],
    "two pointers": ["two pointers", "left and right pointer", "two-pointer"],
    "sliding window": ["sliding window", "window"],
    "stack": ["stack", "monotonic stack", "lifo"],
    "queue / deque": ["queue", "deque", "fifo"],
    "heap / priority queue": ["heap", "min-heap", "max-heap", "priority queue", "heapq"],
    "binary search": ["binary search", "bsearch", "bisect"],
    "tree / bst": ["tree", "binary tree", "bst", "root", "leaf"],
    "graph": ["graph", "adjacency list", "bfs", "dfs"],
    "dynamic programming": ["dynamic programming", "dp table", "memoization", "bottom-up", "tabulation"],
    "trie": ["trie", "prefix tree"],
}

KNOWN_EDGE_CASES = {
    "empty input": ["empty", "length is 0", "len == 0", "null", "none"],
    "single element": ["single element", "len == 1", "one item", "only 1"],
    "duplicate values": ["duplicate", "duplicates", "repeated", "same elements"],
    "negative numbers": ["negative", "less than zero", "< 0"],
    "already sorted": ["already sorted", "sorted array"],
    "large input / scale": ["large input", "10^5", "10^7", "scale", "overflow"],
}

class StateExtractor:
    """
    Background worker that updates structured memory state from candidate turns
    without blocking real-time dialogue generation.
    """

    def __init__(self):
        self._client: Optional[InferenceClient] = None
        self._init_client()

    def _init_client(self):
        token = settings.HF_API_TOKEN.strip() if settings.HF_API_TOKEN else None
        if token:
            try:
                self._client = InferenceClient(api_key=token, timeout=8.0)
            except Exception as e:
                logger.warning(f"Could not initialize HF InferenceClient in StateExtractor: {e}")
                self._client = None
        else:
            self._client = None

    def _parse_existing_state(self, current_state: Union[Dict[str, Any], str, None]) -> Dict[str, Any]:
        """Ensures a sanitized, well-formed state dictionary."""
        base = {
            "data_structures_used": [],
            "claimed_time_complexity": None,
            "claimed_space_complexity": None,
            "identified_edge_cases": [],
            "open_weaknesses": [],
            "key_algorithmic_approach": None,
        }
        if not current_state:
            return base

        if isinstance(current_state, str):
            try:
                parsed = json.loads(current_state)
            except Exception:
                parsed = {}
        elif isinstance(current_state, dict):
            parsed = current_state
        else:
            parsed = {}

        for k in base:
            if k in parsed and parsed[k] is not None:
                base[k] = parsed[k]
        return base

    async def extract_and_update_state(
        self,
        current_state: Union[Dict[str, Any], str, None],
        target_question: Optional[QuestionItem],
        candidate_reply: str,
    ) -> Dict[str, Any]:
        """
        Main entry point: Asynchronously extracts algorithmic features and merges them into state.
        Uses HF Inference with temperature=0.0, falling back to deterministic heuristic parsing.
        """
        existing = self._parse_existing_state(current_state)
        candidate_text = candidate_reply.strip()
        if not candidate_text:
            return existing

        # Ensure client initialized
        if not self._client and settings.HF_API_TOKEN:
            self._init_client()

        # 1. Attempt deterministic LLM extraction if client available
        if self._client:
            q_info = (
                f"Problem: {target_question.text}\n"
                f"Category: {target_question.category}\n"
                f"Target Optimal Complexity: {target_question.optimal_complexity or 'O(N)'}"
                if target_question else "General DSA Problem"
            )

            prompt = (
                f"CURRENT PROBLEM CONTEXT:\n{q_info}\n\n"
                f"PREVIOUS MEMORY STATE:\n{json.dumps(existing, indent=2)}\n\n"
                f"LATEST CANDIDATE REPLY:\n\"\"\"{candidate_text}\"\"\"\n\n"
                f"Extract and return updated JSON memory state:"
            )

            models_to_try = [
                settings.HF_MODEL_ID,
                "google/gemma-2-9b-it",
                "Qwen/Qwen2.5-Coder-32B-Instruct",
            ]

            for model_name in models_to_try:
                if not model_name:
                    continue
                try:
                    def _call():
                        return self._client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                                {"role": "user", "content": prompt}
                            ],
                            max_tokens=400,
                            temperature=0.0,
                        )

                    completion = await anyio.to_thread.run_sync(_call)
                    content = completion.choices[0].message.content
                    extracted = self._clean_and_parse_json(content)
                    if extracted and isinstance(extracted, dict):
                        merged = self._merge_states(existing, extracted)
                        logger.info("Successfully extracted memory state via LLM.")
                        return merged
                except Exception as e:
                    logger.debug(f"StateExtractor LLM extraction error with {model_name}: {e}")

        # 2. Resilient Heuristic Fallback
        logger.debug("Using heuristic rule-based extraction for memory state.")
        return self._heuristic_extract_and_update(existing, target_question, candidate_text)

    def _clean_and_parse_json(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """Strips markdown fences and parses JSON safely."""
        if not raw_text:
            return None
        text = raw_text.strip()
        # Remove ```json ... ``` wrapper if present
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except Exception:
            # Fallback regex search for JSON block { ... }
            match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
        return None

    def _merge_states(self, old_state: Dict[str, Any], new_state: Dict[str, Any]) -> Dict[str, Any]:
        """Merges new extracted state fields with existing cumulative state."""
        merged = dict(old_state)

        # Merge lists with set deduplication preserving order
        for list_key in ["data_structures_used", "identified_edge_cases", "open_weaknesses"]:
            old_list = merged.get(list_key, []) or []
            new_list = new_state.get(list_key, []) or []
            combined = list(old_list)
            for item in new_list:
                if isinstance(item, str) and item.strip() and item not in combined:
                    combined.append(item.strip())
            merged[list_key] = combined

        # Update scalar fields if provided
        if new_state.get("claimed_time_complexity"):
            merged["claimed_time_complexity"] = str(new_state["claimed_time_complexity"]).strip()
        if new_state.get("claimed_space_complexity"):
            merged["claimed_space_complexity"] = str(new_state["claimed_space_complexity"]).strip()
        if new_state.get("key_algorithmic_approach"):
            merged["key_algorithmic_approach"] = str(new_state["key_algorithmic_approach"]).strip()

        return merged

    def _heuristic_extract_and_update(
        self,
        existing: Dict[str, Any],
        target_question: Optional[QuestionItem],
        candidate_text: str,
    ) -> Dict[str, Any]:
        """Heuristic rule-based extractor evaluating candidate keywords, Big-O notations, and code tokens."""
        state = dict(existing)
        lower = candidate_text.lower()

        # 1. Data Structures Detection
        ds_set = set(state.get("data_structures_used", []))
        for canonical, patterns in KNOWN_DATA_STRUCTURES.items():
            if any(p in lower for p in patterns):
                ds_set.add(canonical)
        state["data_structures_used"] = sorted(list(ds_set))

        # 2. Big-O Complexity Extraction
        time_matches = re.findall(r"\b[oO]\s*\(\s*([nN0-9\^a-zA-Z\s\*\+]+)\s*\)", candidate_text)
        if time_matches:
            formatted_matches = [f"O({m.strip()})" for m in time_matches]
            # Look for explicit mention of time vs space
            for match_str in formatted_matches:
                if "space" in lower and not state.get("claimed_space_complexity"):
                    state["claimed_space_complexity"] = match_str
                elif not state.get("claimed_time_complexity"):
                    state["claimed_time_complexity"] = match_str

        # Specific complexity keywords
        if not state.get("claimed_time_complexity"):
            if "linear time" in lower or "o(n)" in lower:
                state["claimed_time_complexity"] = "O(N)"
            elif "quadratic" in lower or "o(n^2)" in lower or "nested loop" in lower:
                state["claimed_time_complexity"] = "O(N^2)"
            elif "logarithmic" in lower or "o(log n)" in lower:
                state["claimed_time_complexity"] = "O(log N)"
            elif "constant time" in lower or "o(1)" in lower:
                state["claimed_time_complexity"] = "O(1)"

        if not state.get("claimed_space_complexity"):
            if "constant space" in lower or "in-place" in lower or "o(1) space" in lower:
                state["claimed_space_complexity"] = "O(1)"
            elif "linear space" in lower or "o(n) space" in lower or "auxiliary array" in lower:
                state["claimed_space_complexity"] = "O(N)"

        # 3. Edge Cases Detection
        edges_set = set(state.get("identified_edge_cases", []))
        for canonical, patterns in KNOWN_EDGE_CASES.items():
            if any(p in lower for p in patterns):
                edges_set.add(canonical)
        state["identified_edge_cases"] = sorted(list(edges_set))

        # 4. Open Weaknesses & Inefficiencies
        weaknesses = list(state.get("open_weaknesses", []))
        optimal = target_question.optimal_complexity if target_question else "O(N)"
        if any(b in lower for b in ["brute force", "o(n^2)", "nested loops"]) and optimal in ["O(N)", "O(N log N)"]:
            msg = f"Suboptimal brute force approach proposed (target is {optimal})"
            if msg not in weaknesses:
                weaknesses.append(msg)
        state["open_weaknesses"] = weaknesses

        # 5. Key Algorithmic Approach
        if not state.get("key_algorithmic_approach"):
            if "two pointers" in lower:
                state["key_algorithmic_approach"] = "Two pointers technique"
            elif "hash map" in lower or "hashmap" in lower:
                state["key_algorithmic_approach"] = "Hash map frequency / index lookup"
            elif "sliding window" in lower:
                state["key_algorithmic_approach"] = "Sliding window optimization"
            elif "binary search" in lower:
                state["key_algorithmic_approach"] = "Binary search on search space"
            elif "dynamic programming" in lower or "dp" in lower:
                state["key_algorithmic_approach"] = "Dynamic programming formulation"
            elif "brute force" in lower:
                state["key_algorithmic_approach"] = "Brute force search"

        return state

state_extractor = StateExtractor()
