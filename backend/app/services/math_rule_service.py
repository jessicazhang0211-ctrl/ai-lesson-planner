import random
import re
import importlib
from typing import Any, Dict, List, Tuple


def _load_sympy_modules():
    sympy = importlib.import_module("sympy")
    geometry = importlib.import_module("sympy.geometry")
    return sympy, geometry


def _load_parse_latex():
    try:
        latex_mod = importlib.import_module("sympy.parsing.latex")
        return getattr(latex_mod, "parse_latex", None)
    except Exception:
        return None


KNOWLEDGE_BASE: Dict[str, Dict[str, Any]] = {
    "分数加减法": {
        "curriculum_standard": "2022版课标：理解同分母与异分母分数加减法算理，能在情境中正确计算并解释步骤。",
        "allowed_prerequisites": ["整数加减法", "分数意义", "通分", "约分"],
        "common_misconceptions": [
            "分子分母分别相加: 1/2 + 1/3 = 2/5",
            "忽略通分直接计算",
            "结果不约分",
        ],
        "verified_examples": [
            {"q": "1/2 + 1/3", "a": "5/6", "explanation": "先通分到6，再相加分子"},
            {"q": "3/4 - 1/8", "a": "5/8", "explanation": "先通分到8，6/8-1/8=5/8"},
        ],
    },
    "一元一次方程": {
        "curriculum_standard": "课标要求：理解方程思想，能通过等式性质解一元一次方程并进行验算。",
        "allowed_prerequisites": ["等式性质", "整数运算", "代入检验"],
        "common_misconceptions": ["移项不变号", "去括号错误", "不做代入检验"],
        "verified_examples": [
            {"q": "2*x + 3 = 11", "a": "4", "explanation": "先减3再除以2"},
        ],
    },
}


def retrieve_math_knowledge(topic: str) -> Dict[str, Any]:
    text = (topic or "").strip()
    if not text:
        return {}

    for key, payload in KNOWLEDGE_BASE.items():
        if key in text or text in key:
            return payload

    # Fallback by keyword.
    if "分数" in text:
        return KNOWLEDGE_BASE["分数加减法"]
    if "方程" in text:
        return KNOWLEDGE_BASE["一元一次方程"]
    return {}


def build_retrieval_context_block(topic: str, lang: str = "zh") -> str:
    context = retrieve_math_knowledge(topic)
    if not context:
        return ""

    if (lang or "zh").lower() == "en":
        return (
            "[CURRICULUM KNOWLEDGE]\n"
            f"- Curriculum standard: {context.get('curriculum_standard', '')}\n"
            f"- Common misconceptions: {context.get('common_misconceptions', [])}\n"
            f"- Verified examples: {context.get('verified_examples', [])}\n"
            "- You must not invent formulas that conflict with this knowledge block.\n"
        )

    return (
        "【课程知识约束】\n"
        f"- 课标要求：{context.get('curriculum_standard', '')}\n"
        f"- 常见错例：{context.get('common_misconceptions', [])}\n"
        f"- 验证例题：{context.get('verified_examples', [])}\n"
        "- 严禁编造与上述知识冲突的公式或结论。\n"
    )


def _normalize_math_expr(text: str) -> str:
    expr = (text or "").strip()
    if "=" in expr:
        expr = expr.split("=", 1)[0].strip()
    expr = expr.replace("×", "*").replace("÷", "/").replace("^", "**")
    expr = re.sub(r"(?<=\d)\s+(?=\d)", "", expr)
    return expr


def _parse_sympy_expr(text: str):
    try:
        sympy, _ = _load_sympy_modules()
    except Exception:
        return None
    expr = _normalize_math_expr(text)
    if not expr:
        return None
    try:
        return sympy.sympify(expr)
    except Exception:
        return None


def _parse_answer(answer: Any):
    try:
        sympy, _ = _load_sympy_modules()
    except Exception:
        return None
    if isinstance(answer, (int, float)):
        return sympy.nsimplify(answer)
    if isinstance(answer, str) and answer.strip():
        return _parse_sympy_expr(answer)
    return None


def _extract_numbers(text: str) -> List[float]:
    matches = re.findall(r"-?\d+(?:\.\d+)?", text or "")
    return [float(x) for x in matches]


def _is_close(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(float(a) - float(b)) <= tol


def _parse_numeric_answer(answer: Any) -> float:
    if isinstance(answer, (int, float)):
        return float(answer)
    if isinstance(answer, str):
        nums = _extract_numbers(answer)
        if nums:
            return float(nums[-1])
    return None


def _verify_arithmetic_layer(question: str, answer: Any) -> Tuple[bool, str]:
    expr = _parse_sympy_expr(question)
    ans_expr = _parse_answer(answer)
    if expr is None or ans_expr is None:
        return False, "算术层无法解析题目或答案"
    try:
        sympy, _ = _load_sympy_modules()
        delta = sympy.simplify(expr - ans_expr)
        if delta == 0:
            return True, ""
        return False, f"算术层不一致: 计算结果={expr}, 给定答案={answer}"
    except Exception as e:
        return False, f"算术层校验异常: {e}"


def _verify_equation_layer(question: str, answer: Any) -> Tuple[bool, str]:
    if "=" not in (question or ""):
        return False, "方程层未检测到等号"
    q = (question or "").replace("^", "**").replace("×", "*").replace("÷", "/")
    try:
        sympy, _ = _load_sympy_modules()
        x = sympy.symbols("x")
        left_raw, right_raw = [p.strip() for p in q.split("=", 1)]
        left = sympy.sympify(left_raw)
        right = sympy.sympify(right_raw)
        sols = sympy.solve(left - right, x)
        if not sols:
            return False, "方程层无可用解"
        ans_num = _parse_numeric_answer(answer)
        if ans_num is None:
            return False, "方程层无法解析答案数值"
        ok = any(_is_close(float(sympy.N(s)), ans_num) for s in sols)
        if ok:
            return True, ""
        return False, f"方程层不一致: 方程解={sols}, 给定答案={answer}"
    except Exception as e:
        return False, f"方程层校验异常: {e}"


def _verify_geometry_layer(question: str, answer: Any) -> Tuple[bool, str]:
    text = (question or "")
    ans_text = str(answer or "")
    nums = _extract_numbers(text)

    if any(k in text for k in ["三角形", "triangle", "边长", "sides"]) and len(nums) >= 3:
        a, b, c = nums[0], nums[1], nums[2]
        valid = (a + b > c) and (a + c > b) and (b + c > a)
        if any(k in ans_text for k in ["能", "可以", "yes", "true", "可构成"]):
            if valid:
                return True, ""
            return False, "几何层不一致: 三角形不等式不成立"
        if any(k in ans_text for k in ["不能", "不可以", "no", "false", "不可构成"]):
            if not valid:
                return True, ""
            return False, "几何层不一致: 三角形不等式成立但答案为否"
        return False, "几何层无法判断答案语义"

    if any(k in text for k in ["角", "angles", "内角和"]) and len(nums) >= 3:
        s = nums[0] + nums[1] + nums[2]
        ans_num = _parse_numeric_answer(answer)
        if ans_num is None:
            return False, "几何层无法解析角度答案"
        if _is_close(s, ans_num):
            return True, ""
        return False, f"几何层不一致: 角度和={s}, 给定答案={answer}"

    return False, "几何层未识别可验证题型"


def _verify_statistics_layer(question: str, answer: Any) -> Tuple[bool, str]:
    text = (question or "")
    nums = _extract_numbers(text)
    if not nums:
        return False, "统计层未提取到样本数据"

    ans_num = _parse_numeric_answer(answer)
    if ans_num is None:
        return False, "统计层无法解析答案数值"

    text_lower = text.lower()
    if any(k in text for k in ["均值", "平均数"]) or "mean" in text_lower:
        mean = sum(nums) / len(nums)
        if _is_close(mean, ans_num):
            return True, ""
        return False, f"统计层不一致: 均值={mean}, 给定答案={answer}"

    if any(k in text for k in ["方差", "variance"]):
        mean = sum(nums) / len(nums)
        var = sum((x - mean) ** 2 for x in nums) / len(nums)
        if _is_close(var, ans_num):
            return True, ""
        return False, f"统计层不一致: 方差={var}, 给定答案={answer}"

    return False, "统计层未识别可验证题型"


def _verify_example_item(question: str, answer: Any, method: str) -> Tuple[bool, str]:
    method_text = (method or "").lower()
    q = question or ""
    q_lower = q.lower()

    # Layer 1: arithmetic
    if method_text in ["sympy计算", "arithmetic", "算术"] or re.search(r"^[\d\s+\-*/().^×÷]+$", q.strip()):
        ok, msg = _verify_arithmetic_layer(q, answer)
        return ok, f"[算术层] {msg}" if not ok else (True, "")

    # Layer 2: equation
    if "=" in q and ("x" in q_lower or "方程" in q):
        ok, msg = _verify_equation_layer(q, answer)
        return ok, f"[方程层] {msg}" if not ok else (True, "")

    # Layer 3: geometry
    if any(k in q for k in ["三角形", "几何", "角", "边长", "triangle", "angle", "sides"]):
        ok, msg = _verify_geometry_layer(q, answer)
        return ok, f"[几何层] {msg}" if not ok else (True, "")

    # Layer 4: statistics
    if any(k in q for k in ["平均", "均值", "方差", "统计", "mean", "variance"]):
        ok, msg = _verify_statistics_layer(q, answer)
        return ok, f"[统计层] {msg}" if not ok else (True, "")

    # Fallback: try arithmetic first, then equation.
    ok, msg = _verify_arithmetic_layer(q, answer)
    if ok:
        return True, ""
    ok2, msg2 = _verify_equation_layer(q, answer)
    if ok2:
        return True, ""
    return False, f"[自动分层] {msg}; {msg2}"


def verify_math_content(json_output: Dict[str, Any], allowed_prerequisites: List[str] = None) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    try:
        sympy, _ = _load_sympy_modules()
    except Exception:
        return False, ["sympy 未安装，无法执行数学自动校验"]
    parse_latex = _load_parse_latex()

    if not isinstance(json_output, dict):
        return False, ["顶层必须是 JSON 对象"]

    prerequisite = json_output.get("prerequisite_knowledge")
    if not isinstance(prerequisite, list) or not prerequisite:
        errors.append("prerequisite_knowledge 必须为非空数组")
    else:
        if allowed_prerequisites:
            allow_set = set(allowed_prerequisites)
            invalid = [x for x in prerequisite if x not in allow_set]
            if invalid:
                errors.append(f"prerequisite_knowledge 包含未授权知识点: {invalid}")

    core_formula = json_output.get("core_formula")
    if not isinstance(core_formula, dict):
        errors.append("core_formula 必须为对象")
    else:
        latex = core_formula.get("latex")
        constraints = core_formula.get("constraints")
        if not isinstance(latex, str) or not latex.strip():
            errors.append("core_formula.latex 不能为空")
        else:
            if parse_latex is not None:
                try:
                    parse_latex(latex)
                except Exception as e:
                    errors.append(f"core_formula.latex 无法解析: {e}")
        if not isinstance(constraints, list) or not [x for x in constraints if isinstance(x, str) and x.strip()]:
            errors.append("core_formula.constraints 必须为非空字符串数组")

    chain = json_output.get("example_chain")
    if not isinstance(chain, list) or not chain:
        errors.append("example_chain 必须为非空数组")
    else:
        for idx, ex in enumerate(chain):
            if not isinstance(ex, dict):
                errors.append(f"example_chain[{idx}] 必须为对象")
                continue
            q = ex.get("question")
            a = ex.get("answer")
            method = (ex.get("verification_method") or "").strip()
            if not isinstance(q, str) or not q.strip():
                errors.append(f"example_chain[{idx}].question 不能为空")
            if a in (None, ""):
                errors.append(f"example_chain[{idx}].answer 不能为空")
            if not method:
                errors.append(f"example_chain[{idx}].verification_method 不能为空")

            # Per-item layered consistency verification.
            ok, reason = _verify_example_item(q if isinstance(q, str) else "", a, method)
            if not ok:
                errors.append(f"example_chain[{idx}] {reason}")

    return len(errors) == 0, errors


class AlgebraProblemGenerator:
    def __init__(self):
        sympy, _ = _load_sympy_modules()
        self.sympy = sympy
        self.x = sympy.symbols("x")

    def generate_linear_equation(self, difficulty: str = "basic") -> Dict[str, Any]:
        diff = (difficulty or "basic").lower()
        if diff == "hard":
            a_min, a_max, b_min, b_max, s_min, s_max = 5, 14, 5, 30, -20, 20
        elif diff == "medium":
            a_min, a_max, b_min, b_max, s_min, s_max = 3, 12, 2, 24, -15, 15
        else:
            a_min, a_max, b_min, b_max, s_min, s_max = 2, 10, 1, 20, -10, 10

        a = random.randint(a_min, a_max)
        b = random.randint(b_min, b_max)
        solution = random.randint(s_min, s_max)
        rhs = a * solution + b

        verified_solution = self.sympy.solve(a * self.x + b - rhs, self.x)[0]
        if int(verified_solution) != int(solution):
            raise RuntimeError("代数题生成校验失败")

        return {
            "equation": f"{a}*x + {b} = {rhs}",
            "solution": int(solution),
            "steps": [
                f"移项: {a}*x = {rhs - b}",
                f"系数化1: x = {(rhs - b) // a}",
                f"代入检验: {a}*({solution})+{b}={rhs}",
            ],
            "verification_method": "sympy.solve",
        }


def generate_triangle_problem() -> Dict[str, Any]:
    _, geometry = _load_sympy_modules()
    Point = geometry.Point
    Triangle = geometry.Triangle

    p1, p2, p3 = Point(0, 0), Point(3, 0), Point(0, 4)
    tri = Triangle(p1, p2, p3)
    hypotenuse = p2.distance(p3)

    return {
        "description": "直角三角形ABC，AB=3，AC=4，A为直角。",
        "properties": {
            "area": float(tri.area),
            "perimeter": float(tri.perimeter.evalf()),
            "hypotenuse": float(hypotenuse.evalf()),
        },
        "geogebra_command": "Polygon((0,0),(3,0),(0,4))",
        "svg": (
            "<svg xmlns='http://www.w3.org/2000/svg' width='220' height='180' viewBox='0 0 220 180'>"
            "<polygon points='20,150 170,150 20,30' fill='none' stroke='#1f2937' stroke-width='2'/>"
            "<text x='84' y='166' font-size='12'>3</text>"
            "<text x='5' y='96' font-size='12'>4</text>"
            "<text x='95' y='85' fill='#b91c1c' font-size='12'>5</text>"
            "</svg>"
        ),
    }


def generate_math_tooling_bundle(topic: str, difficulty: str = "basic", include_geometry: bool = False) -> Dict[str, Any]:
    bundle = {"algebra_problem": AlgebraProblemGenerator().generate_linear_equation(difficulty=difficulty)}

    geometry_keywords = ("几何", "三角形", "勾股", "图形")
    if include_geometry or any(x in (topic or "") for x in geometry_keywords):
        bundle["geometry_figure"] = generate_triangle_problem()

    return bundle
