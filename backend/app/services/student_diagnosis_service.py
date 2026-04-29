from typing import Any, Dict, List


ERROR_LABELS = ["概念", "计算", "审题"]


def classify_error_type(question: Dict[str, Any], student_answer: Any, expected_answer: Any) -> str:
    q_text = str((question or {}).get("stem") or "")
    student_text = str(student_answer or "").strip()
    expected_text = str(expected_answer or "").strip()

    # Heuristic rules for common primary-math mistakes.
    if any(x in q_text for x in ["单位", "米", "厘米", "千克", "小时", "分钟"]):
        if student_text and expected_text and ("单位" not in student_text and any(u in expected_text for u in ["米", "厘米", "千克", "小时", "分钟"])):
            return "审题"
    if any(x in q_text for x in ["方程", "移项", "解方程"]):
        if student_text and expected_text and student_text.replace("-", "") == expected_text.replace("+", ""):
            return "计算"
        return "概念"
    if any(x in q_text for x in ["分数", "通分", "约分"]):
        if "/" in student_text and "/" in expected_text:
            s_parts = student_text.split("/")
            e_parts = expected_text.split("/")
            if len(s_parts) == 2 and len(e_parts) == 2 and s_parts[1] != e_parts[1]:
                return "概念"
        return "计算"

    # Fallback by answer shape.
    if any(ch.isdigit() for ch in student_text):
        return "计算"
    return "审题"


def build_profile_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    knowledge_stats: Dict[str, Dict[str, Any]] = {}
    error_type_stats = {k: 0 for k in ERROR_LABELS}

    for rec in records or []:
        knowledge = str(rec.get("knowledge") or "综合").strip() or "综合"
        is_correct = bool(rec.get("is_correct"))
        if knowledge not in knowledge_stats:
            knowledge_stats[knowledge] = {"correct": 0, "total": 0, "accuracy": 0.0}
        knowledge_stats[knowledge]["total"] += 1
        if is_correct:
            knowledge_stats[knowledge]["correct"] += 1
        else:
            et = rec.get("error_type") or "审题"
            if et not in error_type_stats:
                error_type_stats[et] = 0
            error_type_stats[et] += 1

    for k, v in knowledge_stats.items():
        total = v.get("total", 0) or 0
        correct = v.get("correct", 0) or 0
        v["accuracy"] = round((correct / total), 4) if total else 0.0

    return {
        "knowledge_stats": knowledge_stats,
        "error_type_stats": error_type_stats,
    }


def build_teaching_advice(error_type_stats: Dict[str, int]) -> str:
    if not isinstance(error_type_stats, dict) or not error_type_stats:
        return "当前数据不足，建议继续积累作业数据后再生成备课建议。"

    major = sorted(error_type_stats.items(), key=lambda x: x[1], reverse=True)
    top = major[0][0] if major else "审题"

    advice_map = {
        "概念": "下次应加强概念建构环节，建议增加定义辨析与反例对比。",
        "计算": "下次应加强计算规范训练，建议加入分步验算与易错点对照。",
        "审题": "下次应加强审题策略指导，建议加入关键词圈画和条件复述训练。",
    }
    return advice_map.get(top, "下次应加强基础训练与错题复盘环节。")
