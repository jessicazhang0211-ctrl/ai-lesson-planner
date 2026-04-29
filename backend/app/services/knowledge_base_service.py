import json
import re
from typing import List, Dict, Any

from app.extensions import db
from app.models.knowledge_base_item import KnowledgeBaseItem
from sqlalchemy import or_


def _safe_int(value, default=None):
    try:
        return int(value)
    except Exception:
        return default


def _normalize_text(value) -> str:
    return str(value or "").strip()


def _normalize_tags(raw) -> List[str]:
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    text = _normalize_text(raw)
    if not text:
        return []
    return [x.strip() for x in text.replace("，", ",").split(",") if x.strip()]


def _parse_tags_json(raw: str) -> List[str]:
    try:
        value = json.loads(raw or "")
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]
    except Exception:
        pass
    return []


def _compact_text(value, max_chars=300) -> str:
    text = _normalize_text(value)
    text = re.sub(r"\s+", " ", text)
    if len(text) <= max_chars:
        return text
    return text[: max(0, int(max_chars) - 1)] + "…"


def _build_keywords(topic: str) -> List[str]:
    text = _normalize_text(topic).lower()
    if not text:
        return []
    raw = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{1,}", text)
    out = []
    for item in raw:
        if not item:
            continue
        # Keep short Chinese terms but skip one-letter latin noise.
        if re.fullmatch(r"[a-z0-9]", item):
            continue
        if item not in out:
            out.append(item)
    return out[:16]


def _score_hits(text: str, keywords: List[str], weight: int) -> int:
    base = _normalize_text(text).lower()
    if not base or not keywords:
        return 0
    hits = 0
    for kw in keywords:
        if kw and kw in base:
            hits += 1
    return hits * int(weight)


def _dedupe_signature(topic: str, title: str, content: str) -> str:
    merged = f"{topic}|{title}|{content}".lower()
    merged = re.sub(r"\s+", "", merged)
    return merged[:600]


def save_knowledge_items(created_by: int, items: List[Dict[str, Any]], default_class_id=None, source="manual") -> int:
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        topic = _normalize_text(item.get("topic"))
        content = _normalize_text(item.get("content"))
        title = _normalize_text(item.get("title"))
        class_id = _safe_int(item.get("class_id"), default_class_id)
        tags = _normalize_tags(item.get("tags"))
        if not topic or not content:
            continue
        rows.append(
            KnowledgeBaseItem(
                created_by=int(created_by),
                class_id=class_id,
                topic=topic,
                title=title or None,
                content=content,
                tags_json=json.dumps(tags, ensure_ascii=False) if tags else None,
                source=_normalize_text(item.get("source")) or source,
            )
        )

    if not rows:
        return 0

    db.session.add_all(rows)
    db.session.commit()
    return len(rows)


def list_knowledge_items(created_by: int, class_id=None, topic="", limit=200):
    q = KnowledgeBaseItem.query.filter_by(created_by=int(created_by))
    if class_id is not None:
        q = q.filter_by(class_id=int(class_id))
    topic_kw = _normalize_text(topic)
    if topic_kw:
        like_kw = f"%{topic_kw}%"
        q = q.filter(
            or_(
                KnowledgeBaseItem.topic.like(like_kw),
                KnowledgeBaseItem.title.like(like_kw),
                KnowledgeBaseItem.content.like(like_kw),
            )
        )
    rows = q.order_by(KnowledgeBaseItem.updated_at.desc()).limit(max(1, min(int(limit), 500))).all()

    result = []
    for row in rows:
        tags = []
        try:
            tags = json.loads(row.tags_json) if row.tags_json else []
            if not isinstance(tags, list):
                tags = []
        except Exception:
            tags = []
        result.append(
            {
                "id": row.id,
                "class_id": row.class_id,
                "topic": row.topic,
                "title": row.title or "",
                "content": row.content,
                "tags": tags,
                "source": row.source,
                "updated_at": row.updated_at.strftime("%Y-%m-%d %H:%M:%S") if row.updated_at else "",
            }
        )
    return result


def build_knowledge_injection_context(created_by: int, topic: str, class_id=None, lang="zh", limit=8, max_chars=2200) -> str:
    q = KnowledgeBaseItem.query.filter_by(created_by=int(created_by))
    if class_id is not None:
        q = q.filter(or_(KnowledgeBaseItem.class_id == int(class_id), KnowledgeBaseItem.class_id.is_(None)))

    topic_kw = _normalize_text(topic)
    if topic_kw:
        like_kw = f"%{topic_kw}%"
        q = q.filter(
            or_(
                KnowledgeBaseItem.topic.like(like_kw),
                KnowledgeBaseItem.title.like(like_kw),
                KnowledgeBaseItem.content.like(like_kw),
            )
        )

    safe_limit = max(1, min(int(limit), 20))
    candidate_limit = max(safe_limit * 6, 40)
    rows = q.order_by(KnowledgeBaseItem.updated_at.desc()).limit(candidate_limit).all()
    if not rows:
        return ""

    keywords = _build_keywords(topic_kw)
    scored_rows = []
    for row in rows:
        tags = _parse_tags_json(row.tags_json)
        score = 0
        if keywords:
            score += _score_hits(row.topic, keywords, 6)
            score += _score_hits(row.title or "", keywords, 4)
            score += _score_hits(row.content, keywords, 2)
            score += _score_hits(" ".join(tags), keywords, 3)
            if topic_kw and _normalize_text(row.topic).lower() == topic_kw.lower():
                score += 8
        else:
            score += 1
        scored_rows.append((score, row, tags))

    scored_rows.sort(
        key=lambda x: (
            int(x[0]),
            x[1].updated_at.strftime("%Y-%m-%d %H:%M:%S") if x[1].updated_at else "",
            x[1].id,
        ),
        reverse=True,
    )

    deduped = []
    seen = set()
    for score, row, tags in scored_rows:
        sign = _dedupe_signature(row.topic, row.title or "", row.content)
        if sign in seen:
            continue
        seen.add(sign)
        deduped.append((score, row, tags))
        if len(deduped) >= max(safe_limit * 3, 24):
            break

    if not deduped:
        return ""

    safe_max_chars = max(400, min(int(max_chars), 6000))

    if str(lang or "zh").lower().startswith("en"):
        lines = ["[Custom Knowledge Base Injection]"]
        tail = "Use the above knowledge as grounding context before generating output."
        count = 0
        for _, row, tags in deduped:
            if count >= safe_limit:
                break
            title = _compact_text(row.title or row.topic, max_chars=80)
            content = _compact_text(row.content, max_chars=280)
            tags_text = ", ".join(tags[:6]) if tags else ""
            line = f"{count + 1}. Topic: {row.topic}; Title: {title}; Content: {content}"
            if tags_text:
                line += f"; Tags: {tags_text}"
            if len("\n".join(lines + [line, tail])) > safe_max_chars:
                break
            lines.append(line)
            count += 1
        if count == 0:
            return ""
        lines.append(tail)
        return "\n".join(lines)

    lines = ["【自定义知识库注入】"]
    tail = "请在生成内容前优先吸收以上知识点，避免与知识库内容冲突。"
    count = 0
    for _, row, tags in deduped:
        if count >= safe_limit:
            break
        title = _compact_text(row.title or row.topic, max_chars=80)
        content = _compact_text(row.content, max_chars=280)
        tags_text = "、".join(tags[:6]) if tags else ""
        line = f"{count + 1}. 课题：{row.topic}；标题：{title}；内容：{content}"
        if tags_text:
            line += f"；标签：{tags_text}"
        if len("\n".join(lines + [line, tail])) > safe_max_chars:
            break
        lines.append(line)
        count += 1
    if count == 0:
        return ""
    lines.append(tail)
    return "\n".join(lines)
