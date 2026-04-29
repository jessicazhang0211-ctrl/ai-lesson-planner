import base64
import io
from typing import Any, Dict, List


def build_formula_hints(topic: str, core_formula: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    latex = ""
    if isinstance(core_formula, dict):
        latex = str(core_formula.get("latex") or "").strip()

    if not latex:
        topic_text = topic or ""
        if "分数" in topic_text:
            latex = r"\\frac{a}{b}+\\frac{c}{d}=\\frac{ad+bc}{bd}"
        elif "方程" in topic_text:
            latex = r"ax+b=c"
        elif "平均" in topic_text:
            latex = r"\\bar{x}=\\frac{1}{n}\\sum_{i=1}^{n}x_i"

    if not latex:
        return []

    return [
        {
            "latex": latex,
            "render_engine": "katex",
            "note": "前端可直接用 KaTeX/MathJax 渲染",
        }
    ]


def _render_triangle_png_base64() -> str:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4, 3), dpi=120)
    xs = [0, 3, 0, 0]
    ys = [0, 0, 4, 0]
    ax.plot(xs, ys, "#1f2937", linewidth=2)
    ax.text(1.5, -0.3, "3", fontsize=10)
    ax.text(-0.35, 2.0, "4", fontsize=10)
    ax.text(1.4, 2.1, "5", fontsize=10, color="#b91c1c")
    ax.set_xlim(-0.8, 3.6)
    ax.set_ylim(-0.8, 4.6)
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    ax.set_title("Triangle Sketch")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def build_diagram_suggestions(topic: str) -> List[Dict[str, Any]]:
    topic_text = topic or ""
    if not any(x in topic_text for x in ["几何", "三角形", "勾股", "图形"]):
        return []

    suggestion = {
        "type": "geometry_triangle",
        "description": "直角三角形示意图，可用于边长关系讲解",
        "tool": "matplotlib",
    }

    try:
        suggestion["image_base64_png"] = _render_triangle_png_base64()
        suggestion["render_status"] = "ok"
    except Exception as e:
        suggestion["render_status"] = "unavailable"
        suggestion["reason"] = f"matplotlib unavailable: {type(e).__name__}"
    return [suggestion]
