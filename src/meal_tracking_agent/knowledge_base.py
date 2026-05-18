from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KnowledgeDoc:
    title: str
    content: str


KNOWLEDGE_DOCS: list[KnowledgeDoc] = [
    KnowledgeDoc(
        title="Balanced plate",
        content="A practical balanced plate uses half vegetables, one quarter protein, and one quarter carbs.",
    ),
    KnowledgeDoc(
        title="Protein guidance",
        content="Protein helps with fullness and muscle recovery. Try to include a protein source in each main meal.",
    ),
    KnowledgeDoc(
        title="Calorie deficit",
        content="For fat loss, keep portions controlled and watch calorie-dense extras like fried foods, sugary drinks, and desserts.",
    ),
    KnowledgeDoc(
        title="Meal balance tip",
        content="If a meal is heavy on carbs or fats, balance it with salad, curd, dal, paneer, tofu, eggs, or lean protein.",
    ),
    KnowledgeDoc(
        title="Hydration",
        content="Drinking water through the day supports digestion and can reduce unnecessary snacking.",
    ),
]


def search_knowledge(query: str, limit: int = 3) -> str:
    query_terms = {term.lower() for term in query.split() if term.strip()}
    scored: list[tuple[int, KnowledgeDoc]] = []
    for doc in KNOWLEDGE_DOCS:
        haystack = f"{doc.title} {doc.content}".lower()
        score = sum(1 for term in query_terms if term in haystack)
        if score > 0:
            scored.append((score, doc))

    if not scored:
        scored = [(0, doc) for doc in KNOWLEDGE_DOCS[:limit]]

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = scored[:limit]
    return "\n\n".join(f"{doc.title}: {doc.content}" for _, doc in selected)