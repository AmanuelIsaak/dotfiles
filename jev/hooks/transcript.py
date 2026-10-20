"""Reads the parts of a Claude Code transcript (JSONL) that the Jev hooks need."""
import json


def _text(content, with_tools=False):
    if isinstance(content, str):
        return content
    parts = []
    for b in content or []:
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if t in ("text", "input_text", "output_text"):
            parts.append(b.get("text", ""))
        elif with_tools and t == "tool_use":
            parts.append(f"[tool {b.get('name')}: {json.dumps(b.get('input'), ensure_ascii=False)[:600]}]")
        elif with_tools and t == "tool_result":
            c = b.get("content")
            c = c if isinstance(c, str) else _text(c)
            parts.append(f"[result{' ERROR' if b.get('is_error') else ''}: {c[:600]}]")
    return "\n".join(p for p in parts if p)


def turns(path):
    """-> [(role, content)] in order; skips hook/meta noise."""
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if e.get("type") == "response_item":
                    m = e.get("payload") or {}
                    if m.get("type") == "message" and m.get("role") in ("user", "assistant"):
                        out.append((m["role"], m.get("content")))
                    elif m.get("type") in ("custom_tool_call", "function_call"):
                        out.append(("tool", f"[tool {m.get('name')}: {str(m.get('input') or m.get('arguments') or '')[:600]}]"))
                    elif m.get("type") in ("custom_tool_call_output", "function_call_output"):
                        out.append(("tool", f"[result: {str(m.get('output') or '')[:600]}]"))
                    continue
                if e.get("type") in ("user", "assistant") and not e.get("isMeta"):
                    m = e.get("message") or {}
                    out.append((m.get("role") or e["type"], m.get("content")))
    except OSError:
        pass
    return out


def is_prompt(role, content):
    """A real user prompt, not a tool result carried in a user message."""
    if role != "user":
        return False
    if isinstance(content, str):
        return bool(content.strip())
    return any(isinstance(b, dict) and b.get("type") in ("text", "input_text") for b in content or [])


def last_prompt(path):
    for role, content in reversed(turns(path)):
        if is_prompt(role, content):
            return _text(content)[:4000]
    return ""


def since_last_prompt(path, max_chars=40_000):
    """Last user prompt plus everything after it, tool calls and results included."""
    ts = turns(path)
    start = max((i for i, (r, c) in enumerate(ts) if is_prompt(r, c)), default=0)
    lines = [f"{r.upper()}: {_text(c, with_tools=True)}" for r, c in ts[start:]]
    text = "\n\n".join(l for l in lines if l.split(": ", 1)[1].strip())
    return text if len(text) <= max_chars else text[:4000] + "\n[...]\n" + text[-(max_chars - 4000):]
