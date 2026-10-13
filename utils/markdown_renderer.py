from __future__ import annotations

import bleach
import markdown
from markupsafe import Markup


ALLOWED_TAGS = {"p", "ol", "ul", "li", "strong", "em", "br"}


def render_contract_answer(answer: str) -> Markup:
    """Convert Gemini's Markdown to a small, sanitized HTML subset."""
    rendered_html = markdown.markdown(answer, extensions=["sane_lists"])
    sanitized_html = bleach.clean(
        rendered_html,
        tags=ALLOWED_TAGS,
        attributes={},
        strip=True,
    )
    return Markup(sanitized_html)
