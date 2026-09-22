import json
import logging
import re
from typing import Dict, Any, List, Optional
import anyio
from huggingface_hub import InferenceClient

from backend.config import settings

logger = logging.getLogger("ai_interview.evaluator")

class DSAEvaluatorAgent:
    """
    Technical DSA Interview Evaluation Agent.
    Evaluates candidate performance across 7 core DSA dimensions:
      1. Algorithmic Correctness & Logic
      2. Time & Space Complexity (Big-O)
      3. Data Structure Selection
      4. Edge Case Handling & Rigor
      5. Code Quality & Implementation
      6. Problem-Solving & Optimization Process
      7. Communication & Collaboration
    Enforces strict anti-hallucination rules: chit-chat and greetings are excluded,
    and dimensions lacking proof are marked has_evidence: False with baseline score 1.0.
    """

    def __init__(self):
        self._client: Optional[InferenceClient] = None
        self._init_client()

    def _init_client(self):
        token = settings.HF_API_TOKEN.strip() if settings.HF_API_TOKEN else None
        if token:
            try:
                self._client = InferenceClient(api_key=token, timeout=8.0)
                logger.info(f"Initialized Evaluator HF InferenceClient with model {settings.HF_MODEL_ID}")
            except Exception as e:
                logger.warning(f"Could not initialize HF InferenceClient for evaluator: {e}")
                self._client = None
        else:
            self._client = None

    @staticmethod
    def is_technical_turn(text: str) -> bool:
        """
        Determines whether a candidate turn contains substantive technical discussion,
        algorithmic logic, code, or complexity analysis, as opposed to chit-chat,
        greetings, or biographical introductions.
        """
        if not text or not text.strip():
            return False

        clean = text.strip().lower()

        # Check for code blocks or indentation syntax
        if "```" in text or "    def " in text or "\tdef " in text:
            return True

        # Check for coding syntax tokens
        code_tokens = [
            "def ", "class ", "return ", "for ", "while ", "elif ",
            "else:", "==", "!=", "->", "const ", "let ", "function",
            "=>", "len(", "range(", "append(", "enumerate(", "nums[", "seen["
        ]
        code_count = sum(1 for tok in code_tokens if tok in clean)
        if code_count >= 2:
            return True

        # Check for Big-O / complexity derivations
        complexity_tokens = [
            "o(1)", "o(n)", "o(n^2)", "o(log", "o(nlogn", "o(k", "o(m",
            "time complexity", "space complexity", "auxiliary space",
            "big-o", "asymptotic", "runtime", "memory complexity"
        ]
        if any(tok in clean for tok in complexity_tokens):
            return True

        # Common intro and chit-chat patterns
        intro_patterns = [
            r"^(hi|hello|hey|good\s+morning|good\s+afternoon|good\s+evening)[\s,!.]*",
            r"ready\s+(to\s+start|for\s+the\s+challenge|when\s+you\s+are)",
            r"(i\s+am|i'm)\s+ready",
            r"let'?s\s+(start|begin|do\s+this|go)",
            r"years?\s+of\s+experience",
            r"nice\s+to\s+meet\s+you",
            r"my\s+name\s+is",
            r"excited\s+to\s+be\s+here",
            r"thanks?(\s+you)?",
            r"can\s+you\s+hear\s+me",
            r"let\s+me\s+think",
            r"give\s+me\s+a\s+(second|moment)",
            r"sounds\s+good",
            r"sure",
            r"okay",
            r"ok",
        ]

        sentences = re.split(r"[.!?\n]+", clean)
        non_intro_sentences = []
        for s in sentences:
            s_str = s.strip()
            if not s_str:
                continue
            is_intro_sentence = any(re.search(pat, s_str) for pat in intro_patterns)
            if not is_intro_sentence:
                non_intro_sentences.append(s_str)

        if not non_intro_sentences:
            return False

        remaining_text = " ".join(non_intro_sentences)

        tech_keywords = [
            "hash", "map", "dict", "array", "set", "tree", "pointer", "stack", "queue",
            "heap", "graph", "dp", "sliding window", "binary search", "recursion", "node",
            "iterate", "traverse", "optimal", "brute force", "edge case", "empty", "null",
            "target", "index", "indices", "sorted", "partition", "in-place", "recurrence",
            "base case", "duplicate", "overflow", "trade-off"
        ]
        tech_matches = sum(1 for kw in tech_keywords if kw in remaining_text)
        return tech_matches >= 1

    def _no_technical_evidence_report(self, topic: str) -> Dict[str, Any]:
        """
        Generates an unassessed report (score 1.0) when the candidate only engaged
        in introductory dialogue or chit-chat without attempting technical problem-solving.
        """
        metric_defs = [
            ("algorithmic_logic", "Algorithmic Correctness & Logic", "Candidate did not articulate or demonstrate algorithmic logic or solution steps for the technical problem."),
            ("time_space_complexity", "Time & Space Complexity (Big-O)", "Candidate did not state or derive asymptotic runtime (Time) or auxiliary memory (Space) complexity."),
            ("data_structures", "Data Structure Selection", f"Candidate did not demonstrate data structure choices or trade-offs for {topic}."),
            ("edge_cases", "Edge Case Handling & Rigor", "Candidate did not identify, test, or discuss boundary conditions or edge cases."),
            ("code_quality", "Code Quality & Implementation", "No code implementation or syntax was submitted in dialogue or scratchpad."),
            ("problem_solving", "Problem-Solving & Optimization", "Candidate did not demonstrate technical problem-solving or iterative optimization."),
            ("communication", "Communication & Collaboration", "No substantive technical explanation or discussion was conducted on the problem statement."),
        ]

        dsa_metrics = {}
        for key, name, rationale in metric_defs:
            dsa_metrics[key] = {
                "score": 1.0,
                "name": name,
                "has_evidence": False,
                "rationale": rationale,
                "evidence_quote": "No evidence observed in transcript.",
                "growth_tip": f"Actively engage with the technical problem by presenting your approach, Big-O analysis, and code for {name.lower()}."
            }

        dimension_scores = {
            "communication": 1.0,
            "technical": 1.0,
            "problem_solving": 1.0,
            "behavioral_star": 1.0,
            "adaptability": 1.0,
            "confidence": 1.0,
            "role_alignment": 1.0,
        }

        return {
            "overall_score": 1.0,
            "dimension_scores": dimension_scores,
            "dsa_metrics": dsa_metrics,
            "strengths": [
                "Polite conversational communication during initial session greeting"
            ],
            "improvement_areas": [
                "Attempt the technical problem and explain your algorithmic logic",
                "State Big-O time and space complexity upfront",
                "Implement working code in the interview scratchpad or chat"
            ],
            "recommended_focus_areas": [
                f"{topic} Core Patterns",
                "Technical Interview Problem-Solving Structure",
                "Asymptotic Complexity Derivation"
            ],
            "detailed_feedback": (
                f"This mock interview session on **{topic}** concluded without candidate technical problem-solving or code implementation. "
                "Only introductory dialogue or chit-chat was observed in the transcript. "
                "Because no technical questions were answered or attempted, all technical dimensions are marked as unassessed (No Evidence) with baseline scores. "
                "In your next session, proceed directly into clarifying problem constraints, proposing an algorithm, stating Big-O bounds, and implementing code."
            ),
            "topic": topic,
        }

    def _format_transcript(self, transcript: List[Dict[str, Any]]) -> str:
        """Format raw transcript array into readable dialogue with chronological turn markers."""
        formatted_lines = []
        for i, turn in enumerate(transcript, 1):
            role = turn.get("role", "unknown").upper()
            content = turn.get("content", "").strip()
            formatted_lines.append(f"[Turn {i} - {role}]:\n{content}\n")
        return "\n".join(formatted_lines)

    async def evaluate_interview(
        self,
        topic: str,
        transcript: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Evaluate full interview transcript and generate comprehensive rubric scorecard,
        dimension rationales, strengths, improvement areas, and recommended study topics.
        """
        if not transcript:
            return self._heuristic_evaluation(topic, transcript)

        candidate_turns = [t for t in transcript if t.get("role") == "candidate"]
        technical_turns = [t for t in candidate_turns if self.is_technical_turn(t.get("content", ""))]

        if not technical_turns:
            return self._no_technical_evidence_report(topic)

        candidate_tech_text = " ".join(t.get("content", "") for t in technical_turns)

        if not self._client and settings.HF_API_TOKEN:
            self._init_client()

        # Attempt LLM evaluation if client is configured
        if self._client:
            formatted_transcript = self._format_transcript(transcript)
            system_prompt = (
                "You are an Elite FAANG Senior Staff Software Engineer and Bar Raiser Evaluator.\n"
                f"You are conducting a rigorous, objective evaluation of a Technical DSA Interview on: **{topic}**.\n\n"
                "CRITICAL ANTI-HALLUCINATION & EVIDENCE INTEGRITY PROTOCOL:\n"
                "1. IGNORE CHIT-CHAT & INTRODUCTIONS:\n"
                "   - Filter out candidate greetings ('Hi', 'Hello'), pleasantries ('I am ready', 'Thanks'), and biographical intros ('I have 3 years experience').\n"
                "   - You MUST ONLY evaluate substantive technical problem-solving, algorithms, Big-O bounds, and code.\n"
                "2. ZERO EVIDENCE = SCORE 1.0 (DO NOT FABRICATE):\n"
                "   - If the candidate did NOT state Time or Space complexity (Big-O), set 'has_evidence': false, 'score': 1.0, and 'evidence_quote': 'No evidence observed in transcript.'\n"
                "   - If the candidate did NOT write or submit code, set 'has_evidence': false, 'score': 1.0, and 'evidence_quote': 'No evidence observed in transcript.'\n"
                "   - If the candidate did NOT test or discuss edge cases, set 'has_evidence': false, 'score': 1.0, and 'evidence_quote': 'No evidence observed in transcript.'\n"
                "   - If the candidate did NOT evaluate data structures, set 'has_evidence': false, 'score': 1.0, and 'evidence_quote': 'No evidence observed in transcript.'\n"
                "   - Every 'evidence_quote' MUST be a verbatim substring from the candidate's actual technical turns.\n\n"
                "EVALUATION RUBRIC & SCORING METHODOLOGY (Scale 1.0 to 4.0):\n"
                "- 1.0 (No Evidence / Omitted): Not demonstrated or addressed in dialogue.\n"
                "- 1.1 to 1.9 (Unsatisfactory): Major conceptual errors, unhandled edge cases, brute force without complexity insight.\n"
                "- 2.0 to 2.9 (Developing): Partial logic, basic Big-O awareness, required multiple hints.\n"
                "- 3.0 to 3.5 (Strong / Meets FAANG Bar): Logically sound, derived optimal Time & Space Big-O, proactive with edge cases.\n"
                "- 3.6 to 4.0 (Exceptional / Staff Level): Flawless proof, deep data structure trade-offs, production-grade code.\n\n"
                "REQUIRED JSON OUTPUT FORMAT (Respond with raw JSON only, no markdown):\n"
                "{\n"
                '  "overall_score": 3.4,\n'
                '  "detailed_feedback": "3-4 paragraph executive summary of candidate strengths, trade-off depth, and algorithmic maturity.",\n'
                '  "dsa_metrics": {\n'
                '    "algorithmic_logic": {"score": 3.5, "name": "Algorithmic Correctness & Logic", "has_evidence": true, "rationale": "...", "evidence_quote": "...", "growth_tip": "..."},\n'
                '    "time_space_complexity": {"score": 3.3, "name": "Time & Space Complexity (Big-O)", "has_evidence": true, "rationale": "...", "evidence_quote": "...", "growth_tip": "..."},\n'
                '    "data_structures": {"score": 3.6, "name": "Data Structure Selection", "has_evidence": true, "rationale": "...", "evidence_quote": "...", "growth_tip": "..."},\n'
                '    "edge_cases": {"score": 2.8, "name": "Edge Case Handling & Rigor", "has_evidence": true, "rationale": "...", "evidence_quote": "...", "growth_tip": "..."},\n'
                '    "code_quality": {"score": 3.2, "name": "Code Quality & Implementation", "has_evidence": true, "rationale": "...", "evidence_quote": "...", "growth_tip": "..."},\n'
                '    "problem_solving": {"score": 3.5, "name": "Problem-Solving & Optimization", "has_evidence": true, "rationale": "...", "evidence_quote": "...", "growth_tip": "..."},\n'
                '    "communication": {"score": 3.4, "name": "Communication & Collaboration", "has_evidence": true, "rationale": "...", "evidence_quote": "...", "growth_tip": "..."}\n'
                "  },\n"
                '  "strengths": ["...", "..."],\n'
                '  "improvement_areas": ["...", "..."],\n'
                '  "recommended_focus_areas": ["...", "..."]\n'
                "}"
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Please evaluate this technical interview dialogue:\n\n{formatted_transcript}"}
            ]

            models_to_try = [settings.HF_MODEL_ID, "google/gemma-2-27b-it"]
            for model_name in models_to_try:
                if not model_name:
                    continue
                try:
                    logger.info(f"Calling HF model {model_name} for interview evaluation report...")
                    def _call_hf(m: str):
                        return self._client.chat.completions.create(
                            model=m,
                            messages=messages,
                            max_tokens=1500,
                            temperature=0.2,
                        )

                    completion = await anyio.to_thread.run_sync(_call_hf, model_name)
                    raw_content = completion.choices[0].message.content.strip()
                    parsed = self._extract_json(raw_content)
                    if parsed and "overall_score" in parsed and "dsa_metrics" in parsed:
                        sanitized = self._sanitize_and_standardize(parsed, topic, candidate_tech_text)
                        logger.info(f"Successfully generated LLM evaluation using {model_name}.")
                        return sanitized
                except Exception as e:
                    logger.warning(f"Error calling HF model {model_name} for evaluation: {e}")

        # Fallback to deterministic heuristic evaluation
        logger.info("Using deterministic DSA heuristic evaluation fallback.")
        return self._heuristic_evaluation(topic, transcript)

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON from model output, stripping markdown blocks if present."""
        try:
            return json.loads(text)
        except Exception:
            pass

        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        return None

    def _sanitize_and_standardize(self, parsed: Dict[str, Any], topic: str, candidate_tech_text: str) -> Dict[str, Any]:
        """Validate scores, clamp within 1.0-4.0, and verify candidate proof against actual technical text."""
        dsa_metrics = parsed.get("dsa_metrics", {})
        metric_keys = [
            ("algorithmic_logic", "Algorithmic Correctness & Logic"),
            ("time_space_complexity", "Time & Space Complexity (Big-O)"),
            ("data_structures", "Data Structure Selection"),
            ("edge_cases", "Edge Case Handling & Rigor"),
            ("code_quality", "Code Quality & Implementation"),
            ("problem_solving", "Problem-Solving & Optimization"),
            ("communication", "Communication & Collaboration"),
        ]

        lower_text = candidate_tech_text.lower()
        cleaned_metrics = {}
        total_score = 0.0

        for key, name in metric_keys:
            raw_metric = dsa_metrics.get(key, {})
            score = float(raw_metric.get("score", 2.5))
            score = max(1.0, min(4.0, round(score, 1)))
            has_evidence = bool(raw_metric.get("has_evidence", True))

            # Cross-check proof against actual technical dialogue
            if key == "time_space_complexity":
                comp_markers = ["o(1)", "o(n", "o(log", "o(n^2", "time complexity", "space complexity", "auxiliary space", "runtime"]
                if not any(m in lower_text for m in comp_markers):
                    has_evidence = False
                    score = 1.0
            elif key == "code_quality":
                code_markers = ["def ", "class ", "return ", "for ", "while ", "elif ", "else:", "==", "=>", "const ", "let ", "function"]
                has_code = "```" in candidate_tech_text or any(m in lower_text for m in code_markers)
                if not has_code:
                    has_evidence = False
                    score = 1.0
            elif key == "edge_cases":
                edge_markers = ["empty", "null", "none", "duplicate", "negative", "single", "overflow", "zero", "boundary"]
                if not any(m in lower_text for m in edge_markers):
                    has_evidence = False
                    score = 1.0
            elif key == "data_structures":
                ds_markers = ["hash", "map", "dict", "array", "set", "tree", "pointer", "stack", "queue", "heap", "graph", "dp", "sliding window"]
                if not any(m in lower_text for m in ds_markers):
                    has_evidence = False
                    score = 1.0

            if not has_evidence or score <= 1.0:
                has_evidence = False
                score = 1.0
                evidence_quote = "No evidence observed in transcript."
                rationale = raw_metric.get("rationale", f"Candidate did not demonstrate {name.lower()} during dialogue.")
                if "Evaluated according to" in rationale:
                    rationale = f"Candidate did not articulate or demonstrate {name.lower()} during the technical discussion."
            else:
                evidence_quote = raw_metric.get("evidence_quote", "Observed in candidate technical explanation.")
                rationale = raw_metric.get("rationale", f"Evaluated according to standard {name} rubric criteria.")

            total_score += score
            cleaned_metrics[key] = {
                "score": score,
                "name": name,
                "has_evidence": has_evidence,
                "rationale": rationale,
                "evidence_quote": evidence_quote,
                "growth_tip": raw_metric.get("growth_tip", f"Practice structured drills focused on {name}."),
            }

        overall_score = parsed.get("overall_score")
        if overall_score is None:
            overall_score = round(total_score / len(metric_keys), 1)
        else:
            overall_score = max(1.0, min(4.0, round(float(overall_score), 1)))

        dimension_scores = {
            "communication": cleaned_metrics["communication"]["score"],
            "technical": round((cleaned_metrics["time_space_complexity"]["score"] + cleaned_metrics["data_structures"]["score"]) / 2, 1),
            "problem_solving": round((cleaned_metrics["algorithmic_logic"]["score"] + cleaned_metrics["problem_solving"]["score"]) / 2, 1),
            "behavioral_star": round(cleaned_metrics["communication"]["score"], 1),
            "adaptability": round(cleaned_metrics["edge_cases"]["score"], 1),
            "confidence": round(cleaned_metrics["code_quality"]["score"], 1),
            "role_alignment": round(overall_score, 1),
        }

        strengths = parsed.get("strengths", ["Clear algorithmic reasoning and structured approach"])
        improvements = parsed.get("improvement_areas", ["Validate boundary edge cases before implementation"])
        focus_areas = parsed.get("recommended_focus_areas", [f"{topic} Patterns", "Complexity Analysis"])
        feedback = parsed.get("detailed_feedback", f"Solid technical assessment in {topic}.")

        return {
            "overall_score": overall_score,
            "dimension_scores": dimension_scores,
            "dsa_metrics": cleaned_metrics,
            "strengths": strengths,
            "improvement_areas": improvements,
            "recommended_focus_areas": focus_areas,
            "detailed_feedback": feedback,
            "topic": topic,
        }

    def _heuristic_evaluation(self, topic: str, transcript: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Deterministic, rule-based DSA evaluation based on transcript keywords,
        complexity analysis, edge cases discussed, and scratchpad code presence.
        Strictly ignores chit-chat/greetings, and marks dimensions without proof as has_evidence: False.
        """
        candidate_turns = [t for t in transcript if t.get("role") == "candidate"]
        technical_turns = [t for t in candidate_turns if self.is_technical_turn(t.get("content", ""))]

        if not technical_turns:
            return self._no_technical_evidence_report(topic)

        candidate_tech_text = " ".join(t.get("content", "") for t in technical_turns)
        lower_tech_text = candidate_tech_text.lower()
        num_tech_turns = len(technical_turns)

        def extract_quote(keywords: List[str], max_len: int = 140) -> Optional[str]:
            for turn in technical_turns:
                content = turn.get("content", "").strip()
                lower_content = content.lower()
                for kw in keywords:
                    idx = lower_content.find(kw.lower())
                    if idx != -1:
                        start = max(0, content.rfind(".", 0, idx) + 1)
                        end = content.find(".", idx)
                        if end == -1:
                            end = len(content)
                        else:
                            end = end + 1
                        snippet = content[start:end].strip()
                        if len(snippet) > max_len:
                            snippet = snippet[:max_len] + "..."
                        return snippet
            return None

        # 1. Complexity (Big-O)
        time_keywords = ["o(1)", "o(n)", "o(n^2)", "o(log", "o(nlogn)", "o(k)", "o(m)", "time complexity", "runtime"]
        space_keywords = ["space complexity", "auxiliary space", "o(1) space", "o(n) space", "memory"]

        has_time = any(k in lower_tech_text for k in time_keywords)
        has_space = any(k in lower_tech_text for k in space_keywords)

        if has_time and has_space:
            comp_score = 3.7
            comp_evidence = extract_quote(time_keywords + space_keywords) or "Stated both Time and auxiliary Space Big-O bounds."
            comp_has_evidence = True
            comp_rationale = "Candidate clearly derived both runtime (Time) and auxiliary memory (Space) asymptotic bounds."
            comp_tip = "Continue specifying worst-case vs average-case bounds (e.g. hash table collisions)."
        elif has_time or has_space:
            comp_score = 2.9
            comp_evidence = extract_quote(time_keywords if has_time else space_keywords) or "Stated partial Big-O complexity."
            comp_has_evidence = True
            comp_rationale = "Candidate provided partial complexity analysis, but did not derive both Time and auxiliary Space."
            comp_tip = "Always explicitly analyze both Time complexity and auxiliary Space complexity (including call stack)."
        else:
            comp_score = 1.0
            comp_evidence = "No evidence observed in transcript."
            comp_has_evidence = False
            comp_rationale = "Candidate did not state or derive asymptotic runtime or space complexity (Big-O)."
            comp_tip = "Proactively state Big-O Time (e.g., O(N)) and Space bounds before and after implementing your solution."

        # 2. Data Structures
        ds_keywords = ["hash", "map", "dict", "array", "set", "tree", "pointer", "stack", "queue", "heap", "graph", "dp", "sliding window", "trie", "matrix"]
        found_ds = [k for k in ds_keywords if k in lower_tech_text]
        if len(found_ds) >= 3:
            ds_score = 3.8
            ds_has_evidence = True
            ds_evidence = extract_quote(found_ds) or f"Selected optimal data structures ({', '.join(found_ds[:3])})."
            ds_rationale = f"Demonstrated appropriate data structure selection ({', '.join(found_ds[:3])}) suited for {topic}."
            ds_tip = "Analyze cache locality and memory overhead when choosing structures."
        elif len(found_ds) >= 1:
            ds_score = 3.1
            ds_has_evidence = True
            ds_evidence = extract_quote(found_ds) or f"Referenced data structures: {', '.join(found_ds)}."
            ds_rationale = f"Identified data structure ({found_ds[0]}) for the problem."
            ds_tip = "Discuss trade-offs between competing data structures (e.g. array vs hash table space trade-off)."
        else:
            ds_score = 1.0
            ds_has_evidence = False
            ds_evidence = "No evidence observed in transcript."
            ds_rationale = f"Candidate did not explicitly mention or evaluate data structures for {topic}."
            ds_tip = f"Explicitly explain which data structure is best suited for {topic} and why."

        # 3. Edge Cases
        edge_keywords = ["empty", "null", "none", "duplicate", "negative", "single", "overflow", "boundary", "zero", "odd", "even", "constraints"]
        found_edges = [k for k in edge_keywords if k in lower_tech_text]
        if len(found_edges) >= 2:
            edge_score = 3.6
            edge_has_evidence = True
            edge_evidence = extract_quote(found_edges) or f"Handled edge cases: {', '.join(found_edges)}."
            edge_rationale = f"Proactively considered edge cases and boundary conditions ({', '.join(found_edges[:3])})."
            edge_tip = "State boundary invariants before executing loop constructs."
        elif len(found_edges) == 1:
            edge_score = 2.8
            edge_has_evidence = True
            edge_evidence = extract_quote(found_edges) or f"Mentioned edge condition: {found_edges[0]}."
            edge_rationale = f"Identified an edge condition ({found_edges[0]}), but did not test multiple boundary scenarios."
            edge_tip = "Proactively write out an edge-case checklist before writing code."
        else:
            edge_score = 1.0
            edge_has_evidence = False
            edge_evidence = "No evidence observed in transcript."
            edge_rationale = "Candidate did not identify, discuss, or handle boundary conditions or edge cases."
            edge_tip = "Always check edge cases: empty input, single element, extreme/negative values, and duplicates."

        # 4. Code Quality & Implementation
        code_markers = ["def ", "class ", "return ", "for ", "while ", "elif ", "else:", "==", "int ", "const ", "let ", "function", "=>"]
        code_count = sum(1 for m in code_markers if m in lower_tech_text)
        has_code_block = "```" in candidate_tech_text

        if has_code_block or code_count >= 3:
            code_score = 3.7 if (has_code_block and code_count >= 3) else 3.2
            code_has_evidence = True
            code_evidence = extract_quote(["def ", "return ", "for ", "while ", "class "]) or (technical_turns[0].get("content", "")[:120])
            code_rationale = "Provided structured code implementation with identifiable variables and syntax."
            code_tip = "Keep functions modular, practice guard clauses, and avoid premature micro-optimizations."
        elif code_count >= 1:
            code_score = 2.5
            code_has_evidence = True
            code_evidence = extract_quote(code_markers) or "Partial code snippet submitted."
            code_rationale = "Submitted partial code or pseudocode constructs, but lacked complete implementation."
            code_tip = "Write complete, executable code in the editor rather than high-level pseudocode."
        else:
            code_score = 1.0
            code_has_evidence = False
            code_evidence = "No evidence observed in transcript."
            code_rationale = "No code implementation or executable syntax was submitted by the candidate."
            code_tip = "Implement complete solution code in the editor or chat response."

        # 5. Algorithmic Logic
        logic_keywords = ["approach", "algorithm", "solve", "iterate", "traverse", "target", "pointer", "hash", "check", "optimal", "calculate", "find"]
        found_logic = [k for k in logic_keywords if k in lower_tech_text]
        if len(found_logic) >= 2 or num_tech_turns >= 2:
            logic_score = 3.6 if (code_has_evidence and len(found_logic) >= 2) else 3.0
            logic_has_evidence = True
            logic_evidence = extract_quote(found_logic) or technical_turns[0].get("content", "")[:120]
            logic_rationale = "Articulated structured algorithmic approach to resolve the problem."
            logic_tip = "State loop invariants explicitly and trace an example walkthrough before coding."
        elif len(found_logic) == 1:
            logic_score = 2.4
            logic_has_evidence = True
            logic_evidence = extract_quote(found_logic) or "Partial algorithmic concept."
            logic_rationale = "Outlined high-level concept, but lacked detailed step-by-step logic."
            logic_tip = "Structure your solution by breaking it into sub-problems before implementing."
        else:
            logic_score = 1.0
            logic_has_evidence = False
            logic_evidence = "No evidence observed in transcript."
            logic_rationale = "Candidate did not articulate an algorithmic strategy or solution logic."
            logic_tip = "Explain your proposed algorithmic strategy step-by-step before writing code."

        # 6. Problem Solving & Optimization
        opt_keywords = ["optimize", "brute force", "better", "efficient", "two pointer", "trade-off", "reduce"]
        found_opt = [k for k in opt_keywords if k in lower_tech_text]
        if len(found_opt) >= 2:
            ps_score = 3.7
            ps_has_evidence = True
            ps_evidence = extract_quote(found_opt) or "Explored algorithmic trade-offs and optimizations."
            ps_rationale = "Demonstrated ability to iterate toward optimal complexity and discuss trade-offs."
            ps_tip = "Practice identifying bottlenecks immediately in the brute force approach."
        elif len(found_opt) == 1:
            ps_score = 3.0
            ps_has_evidence = True
            ps_evidence = extract_quote(found_opt) or "Mentioned optimization direction."
            ps_rationale = "Recognized optimization opportunity during problem discussion."
            ps_tip = "Systematically benchmark time and space trade-offs between solutions."
        else:
            if logic_has_evidence or code_has_evidence:
                ps_score = 2.6
                ps_has_evidence = True
                ps_evidence = "Applied direct solution methodology to problem prompt."
                ps_rationale = "Addressed the problem directly without comparing alternate algorithmic trade-offs."
                ps_tip = "Start with a brute force baseline, analyze its bottleneck, and explain how to optimize it."
            else:
                ps_score = 1.0
                ps_has_evidence = False
                ps_evidence = "No evidence observed in transcript."
                ps_rationale = "Candidate did not demonstrate technical problem-solving or iterative optimization."
                ps_tip = "Practice structured problem decomposition."

        # 7. Technical Communication
        words_in_tech = len(candidate_tech_text.split())
        if words_in_tech >= 60 and num_tech_turns >= 2:
            comm_score = 3.6
            comm_has_evidence = True
            comm_evidence = technical_turns[0].get("content", "")[:120]
            comm_rationale = f"Clear technical communication across {num_tech_turns} technical dialogue turns."
            comm_tip = "Structure responses with clear problem-solving phases (Understand, Explore, Plan, Code, Test)."
        elif words_in_tech >= 20:
            comm_score = 3.0
            comm_has_evidence = True
            comm_evidence = technical_turns[0].get("content", "")[:120]
            comm_rationale = "Communicated technical ideas adequately during the session."
            comm_tip = "Vocalize your thought process proactively rather than waiting for questions."
        else:
            comm_score = 2.0
            comm_has_evidence = True
            comm_evidence = technical_turns[0].get("content", "")[:100] if technical_turns else "Brief technical response."
            comm_rationale = "Very brief technical communication; provided minimal explanation of thoughts."
            comm_tip = "Provide richer verbal explanations of your internal reasoning and design decisions."

        dsa_metrics = {
            "algorithmic_logic": {
                "score": logic_score,
                "name": "Algorithmic Correctness & Logic",
                "has_evidence": logic_has_evidence,
                "rationale": logic_rationale,
                "evidence_quote": logic_evidence,
                "growth_tip": logic_tip,
            },
            "time_space_complexity": {
                "score": comp_score,
                "name": "Time & Space Complexity (Big-O)",
                "has_evidence": comp_has_evidence,
                "rationale": comp_rationale,
                "evidence_quote": comp_evidence,
                "growth_tip": comp_tip,
            },
            "data_structures": {
                "score": ds_score,
                "name": "Data Structure Selection",
                "has_evidence": ds_has_evidence,
                "rationale": ds_rationale,
                "evidence_quote": ds_evidence,
                "growth_tip": ds_tip,
            },
            "edge_cases": {
                "score": edge_score,
                "name": "Edge Case Handling & Rigor",
                "has_evidence": edge_has_evidence,
                "rationale": edge_rationale,
                "evidence_quote": edge_evidence,
                "growth_tip": edge_tip,
            },
            "code_quality": {
                "score": code_score,
                "name": "Code Quality & Implementation",
                "has_evidence": code_has_evidence,
                "rationale": code_rationale,
                "evidence_quote": code_evidence,
                "growth_tip": code_tip,
            },
            "problem_solving": {
                "score": ps_score,
                "name": "Problem-Solving & Optimization",
                "has_evidence": ps_has_evidence,
                "rationale": ps_rationale,
                "evidence_quote": ps_evidence,
                "growth_tip": ps_tip,
            },
            "communication": {
                "score": comm_score,
                "name": "Communication & Collaboration",
                "has_evidence": comm_has_evidence,
                "rationale": comm_rationale,
                "evidence_quote": comm_evidence,
                "growth_tip": comm_tip,
            }
        }

        overall = round(sum(m["score"] for m in dsa_metrics.values()) / len(dsa_metrics), 1)

        dimension_scores = {
            "communication": dsa_metrics["communication"]["score"],
            "technical": round((dsa_metrics["time_space_complexity"]["score"] + dsa_metrics["data_structures"]["score"]) / 2, 1),
            "problem_solving": round((dsa_metrics["algorithmic_logic"]["score"] + dsa_metrics["problem_solving"]["score"]) / 2, 1),
            "behavioral_star": round(dsa_metrics["communication"]["score"], 1),
            "adaptability": round(dsa_metrics["edge_cases"]["score"], 1),
            "confidence": round(dsa_metrics["code_quality"]["score"], 1),
            "role_alignment": round(overall, 1),
        }

        strengths = []
        if comp_has_evidence and comp_score >= 3.0:
            strengths.append("Clear derivation of asymptotic Big-O bounds")
        if ds_has_evidence and ds_score >= 3.0:
            strengths.append(f"Effective application of relevant data structures for {topic}")
        if edge_has_evidence and edge_score >= 3.0:
            strengths.append("Proactive identification and handling of edge cases")
        if code_has_evidence and code_score >= 3.0:
            strengths.append("Structured and readable code implementation")
        if logic_has_evidence and logic_score >= 3.0:
            strengths.append("Sound algorithmic approach and logic decomposition")
        if not strengths:
            strengths.append(f"Initial technical engagement with the {topic} problem statement")

        improvement_areas = []
        if not comp_has_evidence:
            improvement_areas.append("Derive and state Big-O Time and auxiliary Space complexity bounds")
        if not edge_has_evidence:
            improvement_areas.append("Identify and test boundary conditions (empty inputs, single elements, duplicates)")
        if not code_has_evidence:
            improvement_areas.append("Write complete, runnable code implementation in the scratchpad")
        if not ds_has_evidence:
            improvement_areas.append(f"Analyze data structure trade-offs specific to {topic}")
        if not improvement_areas:
            improvement_areas.append("Practice formulating formal loop invariants and boundary assertions")

        return {
            "overall_score": overall,
            "dimension_scores": dimension_scores,
            "dsa_metrics": dsa_metrics,
            "strengths": strengths,
            "improvement_areas": improvement_areas,
            "recommended_focus_areas": [
                f"{topic} Optimization Patterns",
                "Amortized Complexity Analysis",
                "Boundary Condition Invariants"
            ],
            "detailed_feedback": (
                f"The candidate completed a technical mock interview on **{topic}**. "
                f"Demonstrated algorithmic intuition and structured problem-solving. "
                f"To reach the senior staff tier, focus on proactively articulating edge case invariants "
                f"and clarifying space-time trade-offs upfront before diving into implementation."
            ),
            "topic": topic,
        }

evaluator_agent = DSAEvaluatorAgent()
