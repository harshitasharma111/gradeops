from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from typing import TypedDict, List
from dotenv import load_dotenv
import os
import json

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.1
)

class GradingState(TypedDict):
    student_answer: str
    rubric: dict
    question: str
    max_marks: int
    evaluated_conditions: List[dict]
    total_score: int
    justification: str
    confidence: float
    needs_urgent_review: bool

def evaluate_conditions(state: GradingState) -> GradingState:
    conditions = state["rubric"].get("conditions", [])
    evaluated = []

    for condition in conditions:
        prompt = f"""You are a strict but fair exam grader.

Question: {state["question"]}

Student Answer: {state["student_answer"]}

Rubric Condition: "{condition["condition"]}"
Marks for this condition: {condition["marks"]}

Does the student answer satisfy this condition?
Reply in this exact JSON format with no extra text:
{{
    "condition": "{condition["condition"]}",
    "satisfied": true or false,
    "marks_awarded": number between 0 and {condition["marks"]},
    "reason": "one sentence explanation"
}}"""

        response = llm.invoke([HumanMessage(content=prompt)])
        
        try:
            clean = response.content.strip().replace("```json", "").replace("```", "")
            result = json.loads(clean)
            evaluated.append(result)
        except:
            evaluated.append({
                "condition": condition["condition"],
                "satisfied": False,
                "marks_awarded": 0,
                "reason": "Could not evaluate this condition"
            })

    state["evaluated_conditions"] = evaluated
    return state

def calculate_score(state: GradingState) -> GradingState:
    total = sum(c.get("marks_awarded", 0) for c in state["evaluated_conditions"])
    state["total_score"] = min(total, state["max_marks"])
    return state

def generate_justification(state: GradingState) -> GradingState:
    conditions_summary = "\n".join([
        f"- {c['condition']}: {'✓' if c['satisfied'] else '✗'} ({c['marks_awarded']} marks) — {c['reason']}"
        for c in state["evaluated_conditions"]
    ])

    prompt = f"""You are writing feedback for a student exam answer.

Question: {state["question"]}
Student Answer: {state["student_answer"]}
Total Score: {state["total_score"]}/{state["max_marks"]}

Condition Breakdown:
{conditions_summary}

Write a clear, professional 2-3 sentence justification for this grade.
Be specific about what the student did well and what was missing.
Write in paragraph form, no bullet points."""

    response = llm.invoke([HumanMessage(content=prompt)])
    state["justification"] = response.content.strip()
    return state

def confidence_check(state: GradingState) -> GradingState:
    satisfied_count = sum(1 for c in state["evaluated_conditions"] if c["satisfied"])
    total_conditions = len(state["evaluated_conditions"])
    
    if total_conditions == 0:
        state["confidence"] = 0.0
        state["needs_urgent_review"] = True
        return state

    confidence = satisfied_count / total_conditions
    score_ratio = state["total_score"] / state["max_marks"] if state["max_marks"] > 0 else 0
    final_confidence = (confidence + score_ratio) / 2
    state["confidence"] = round(final_confidence, 2)
    state["needs_urgent_review"] = final_confidence < 0.4
    return state

def build_grading_graph():
    graph = StateGraph(GradingState)
    graph.add_node("evaluate_conditions", evaluate_conditions)
    graph.add_node("calculate_score", calculate_score)
    graph.add_node("generate_justification", generate_justification)
    graph.add_node("confidence_check", confidence_check)
    graph.set_entry_point("evaluate_conditions")
    graph.add_edge("evaluate_conditions", "calculate_score")
    graph.add_edge("calculate_score", "generate_justification")
    graph.add_edge("generate_justification", "confidence_check")
    graph.add_edge("confidence_check", END)
    return graph.compile()

grading_pipeline = build_grading_graph()

def grade_answer(question: str, student_answer: str, rubric: dict) -> dict:
    initial_state = GradingState(
        student_answer=student_answer,
        rubric=rubric,
        question=question,
        max_marks=rubric.get("max_marks", 10),
        evaluated_conditions=[],
        total_score=0,
        justification="",
        confidence=0.0,
        needs_urgent_review=False
    )
    result = grading_pipeline.invoke(initial_state)
    return {
        "total_score": result["total_score"],
        "max_marks": result["max_marks"],
        "justification": result["justification"],
        "confidence": result["confidence"],
        "needs_urgent_review": result["needs_urgent_review"],
        "condition_breakdown": result["evaluated_conditions"]
    }
