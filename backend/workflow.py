from __future__ import annotations

import re
from typing import Any


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [part.strip(" -•") for part in parts if len(part.strip(" -•")) > 3]


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        value = item.strip()
        key = value.lower()
        if value and key not in seen:
            result.append(value)
            seen.add(key)
    return result


def title_for(problem: str) -> str:
    lowered = problem.lower()
    if any(word in lowered for word in ["workload", "job", "manager", "career", "office"]):
        return "Workload and career direction"
    if any(word in lowered for word in ["relationship", "partner", "friend"]):
        return "Relationship and next steps"
    words = re.findall(r"[A-Za-z0-9']+", problem)
    return " ".join(words[:6]).capitalize() or "Untitled thinking case"


def context_from_problem(problem: str, about: str = "not_sure") -> dict[str, Any]:
    lowered = problem.lower()
    sentences = split_sentences(problem)
    facts = []
    if sentences:
        facts.extend(sentences[:4])
    if "fresher" in lowered:
        facts.append("The person is early in their career.")
    if "workload" in lowered or "too high" in lowered or "too much work" in lowered:
        facts.append("The current workload feels high and difficult to sustain.")
    if "beyond normal hours" in lowered or "late" in lowered or "overtime" in lowered:
        facts.append("Work is sometimes extending beyond normal hours.")
    facts = unique(facts)[:6]

    constraints = []
    if any(word in lowered for word in ["income", "salary", "money", "financial"]):
        constraints.append("Income or financial stability matters right now.")
    if any(word in lowered for word in ["time", "busy", "workload", "multiple tasks"]):
        constraints.append("Available time is limited by current demands.")
    if any(word in lowered for word in ["energy", "tired", "exhausted", "burnout"]):
        constraints.append("Energy is limited, which affects follow-through.")
    if any(word in lowered for word in ["manager", "boss", "say no", "push back"]):
        constraints.append("There is concern about how pushback or reprioritization may be received.")
    if not constraints:
        constraints.append("The person wants to make progress without creating a new problem.")
    constraints = unique(constraints)[:5]

    goal = "Understand the situation clearly enough to choose a realistic next step."
    if any(word in lowered for word in ["switch job", "change job", "new job", "quit", "leave"]):
        goal = "Create a realistic path toward a future job change without making a rushed decision."
    elif any(word in lowered for word in ["decide", "should i", "what should"]):
        goal = "Make a considered decision while keeping the important trade-offs visible."

    stakeholders = ["The person making the decision"]
    if any(word in lowered for word in ["manager", "boss", "team", "workload", "job"]):
        stakeholders += ["Manager or team", "Future self"]
    if any(word in lowered for word in ["friend", "partner", "family", "parent"]):
        stakeholders.append("People close to the person")
    stakeholders = unique(stakeholders)

    assumptions = [
        {"assumption": "The current framing captures the whole problem.", "why": "A wider framing may reveal lower-risk options.", "test": "Describe what would still be difficult if the obvious solution were unavailable."},
        {"assumption": "The most visible constraint is the most important one.", "why": "Time, energy, money, and relationship risk can pull in different directions.", "test": "Rank the constraints and note what evidence supports the ranking."},
    ]
    if "say no" in lowered or "non-negotiable" in lowered:
        assumptions.append({"assumption": "All additional work is non-negotiable.", "why": "Some work may be reprioritized even if saying no feels unsafe.", "test": "Ask which task should take priority if capacity is limited."})

    unknowns = [
        "Which constraint matters most right now?",
        "What flexibility exists that has not been tested yet?",
        "What would a good-enough next month look like?",
    ]
    if "manager" in lowered or "boss" in lowered:
        unknowns[1] = "How would the manager respond to a specific priority or deadline conversation?"
    if "income" in lowered or "salary" in lowered:
        unknowns.append("How much financial runway is available if plans change?")

    return {
        "goal": goal,
        "facts": facts,
        "constraints": constraints,
        "stakeholders": stakeholders,
        "assumptions": assumptions,
        "unknowns": unique(unknowns)[:5],
        "about": about,
    }


def question_from_context(context: dict[str, Any], problem: str) -> dict[str, Any]:
    lowered = problem.lower()
    if any(word in lowered for word in ["workload", "too much work", "busy"]):
        question = "What is the biggest constraint right now?"
        options = ["Lack of time", "Lack of energy", "Fear of manager reaction", "Unclear expectations", "Other"]
    elif any(word in lowered for word in ["relationship", "partner"]):
        question = "What outcome are you most trying to protect?"
        options = ["Trust", "Stability", "Honesty", "Personal boundaries", "Not sure yet"]
    else:
        question = "Which part of this situation feels most urgent to understand?"
        options = ["What is actually happening", "What could change", "What I can control", "The likely trade-offs", "Not sure yet"]
    return {"prompt": question, "options": options, "answer": None, "skipped": False}


def analysis_from_context(context: dict[str, Any], problem: str, answer: str = "", skipped: bool = False) -> dict[str, Any]:
    lowered = problem.lower()
    answer_label = answer.strip() if answer.strip() else "Not specified"
    is_work = any(word in lowered for word in ["workload", "job", "manager", "career", "office"])
    if is_work:
        connections = [
            {"label": "High workload", "detail": "less recovery time"},
            {"label": "Less recovery time", "detail": "lower energy for preparation"},
            {"label": "Lower preparation energy", "detail": "slower progress toward a job change"},
            {"label": "Slower progress", "detail": "longer exposure to the current workload"},
        ]
        reframing = {"current": "Should I quit or just endure this?", "possible": "How can I create a realistic path toward changing jobs without immediately losing income?"}
        perspectives = [
            {"name": "The person in the situation", "focus": ["Income", "Energy", "Career growth"], "voice": "Needs progress that is possible on a tired week."},
            {"name": "Manager or team", "focus": ["Deadlines", "Reliability", "Delivery risk"], "voice": "May not see the hidden cost of competing priorities."},
            {"name": "Future self", "focus": ["Skills", "Mobility", "Sustainable workload"], "voice": "Benefits from small, consistent steps rather than an all-or-nothing move."},
        ]
        options = [
            {"title": "Create a protected weekly preparation window", "why": "Builds job-change momentum without an immediate exit.", "upside": "Progress can compound even in small blocks.", "downside": "The time may be vulnerable during peak workload.", "risk": "Low to medium", "effort": "Medium", "reversibility": "High", "unknowns": "Whether the window can be protected consistently."},
            {"title": "Have a priority-and-capacity conversation", "why": "Tests whether the workload is truly fixed or simply unexamined.", "upside": "May reduce overload and clarify expectations.", "downside": "Requires a specific, non-accusatory conversation.", "risk": "Medium", "effort": "Medium", "reversibility": "High", "unknowns": "How the manager will respond."},
            {"title": "Prepare quietly while gathering evidence", "why": "Preserves income while making the next move more informed.", "upside": "Creates optionality instead of forcing a binary decision.", "downside": "The current situation may continue for longer.", "risk": "Low", "effort": "Low to medium", "reversibility": "High", "unknowns": "How long the current pace remains sustainable."},
        ]
        contradictions = ["The person wants to change jobs but needs current income to remain stable.", "Preparation requires energy, while the current workload is consuming that energy.", "Saying no feels risky, yet not clarifying priorities also carries risk."]
        blind_spots = ["Treating the choice as quit versus endure may hide intermediate moves.", "The cost of unclear priorities may be counted as personal weakness rather than a coordination problem.", "A small protected block can be a meaningful strategy even if it does not solve the whole workload."]
        synthesis = {"insight": "The problem is not only workload; it is the feedback loop between workload, energy, and future optionality.", "uncertainty": "It is not yet clear which tasks are genuinely non-negotiable or how much flexibility exists.", "tradeoff": "Protecting income and energy may slow the job search, while moving faster may increase short-term instability.", "next_step": "Choose one small, reversible action that tests flexibility without requiring a final career decision.", "other_paths": ["Ask for priority clarification", "Document workload for two weeks", "Protect one preparation block", "Revisit the plan after new evidence"]}
    else:
        connections = [
            {"label": "Unclear situation", "detail": "more mental load"},
            {"label": "More mental load", "detail": "narrower view of options"},
            {"label": "Narrower view", "detail": "more pressure to choose quickly"},
        ]
        reframing = {"current": "What is the one correct answer?", "possible": "What would help me make the next decision with better information and fewer avoidable risks?"}
        perspectives = [
            {"name": "The person in the situation", "focus": ["Needs", "Energy", "Values"], "voice": "Experiences the immediate emotional and practical cost."},
            {"name": "Other people involved", "focus": ["Expectations", "Impact", "Constraints"], "voice": "May be operating with different information or incentives."},
            {"name": "Future self", "focus": ["Learning", "Sustainability", "Options"], "voice": "Benefits from decisions that preserve future choice."},
        ]
        options = [
            {"title": "Gather one missing piece of evidence", "why": "Reduces uncertainty before committing.", "upside": "Keeps the next move grounded.", "downside": "Does not resolve everything immediately.", "risk": "Low", "effort": "Low", "reversibility": "High", "unknowns": "Whether the evidence will change the choice."},
            {"title": "Try a small reversible experiment", "why": "Tests a hypothesis in the real situation.", "upside": "Turns an abstract concern into information.", "downside": "May require a little discomfort.", "risk": "Low to medium", "effort": "Medium", "reversibility": "High", "unknowns": "How others will respond."},
            {"title": "Pause and define a minimum acceptable outcome", "why": "Makes trade-offs explicit before acting.", "upside": "Prevents urgency from choosing for you.", "downside": "Can feel slower at first.", "risk": "Low", "effort": "Low", "reversibility": "High", "unknowns": "Whether the minimum is realistic."},
        ]
        contradictions = ["The situation feels urgent, but the most useful information may take time to gather.", "A desire for certainty can compete with the need to take a small step."]
        blind_spots = ["Assuming that the first stated problem is the only problem.", "Treating uncertainty as a reason to wait indefinitely rather than a signal to run a small test.", "Overlooking what the other people involved may not know yet."]
        synthesis = {"insight": "A better decision may come from improving the question, not forcing an answer immediately.", "uncertainty": "The most decision-changing fact has not been confirmed yet.", "tradeoff": "Speed provides relief, while more context may reduce avoidable risk.", "next_step": "Choose one low-risk action that produces useful information this week.", "other_paths": ["Ask a focused question", "Write down the minimum acceptable outcome", "Talk to the person most affected", "Set a review point"]}
    return {"known": context.get("facts", []), "unknown": context.get("unknowns", []) + ([f"The answer to the clarification question: {answer_label}"] if skipped or answer.strip() else []), "critical_unknowns": context.get("unknowns", [])[:2], "assumptions": context.get("assumptions", []), "perspectives": perspectives, "connections": connections, "contradictions": contradictions, "blind_spots": blind_spots, "reframe": reframing, "options": options, "synthesis": synthesis, "question_answer": answer_label, "question_skipped": skipped, "problem_as_understood": context.get("goal", "Understand the situation clearly enough to choose a realistic next step."), "mode": "structured fallback analysis"}
