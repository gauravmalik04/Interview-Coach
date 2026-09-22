from typing import Annotated, TypedDict, List, Dict, Any, Optional
from langgraph.graph.message import add_messages

class InterviewState(TypedDict):
    """LangGraph state schema for adaptive technical interview session."""
    
    # Message stream containing system, human (candidate), and AI messages
    messages: Annotated[list, add_messages]
    
    # Session & Candidate identifiers
    candidate_id: str
    interview_id: str
    topic: str
    
    # Question pool & tracking
    question_pool: List[Dict[str, Any]]
    current_question_index: int
    questions_asked: int
    probing_count: int  # Max 2 follow-ups per question
    
    # Phase machine: intro -> warm_up -> core -> probing -> closing -> done
    phase: str
    
    # Serialized transcript for evaluation
    transcript: List[Dict[str, Any]]

class EvaluatorState(TypedDict):
    """LangGraph state schema for evaluation rubric scoring."""
    candidate_id: str
    interview_id: str
    topic: str
    transcript: List[Dict[str, Any]]
    formatted_transcript: str
    report_data: Optional[Dict[str, Any]]
    is_saved: bool
    is_embedded: bool

class CoachState(TypedDict):
    """LangGraph state schema for vector-retrieval RAG coaching."""
    candidate_id: str
    query: str
    retrieved_contexts: List[Dict[str, Any]]
    response: str
