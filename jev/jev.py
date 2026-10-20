"""Minimal Jev client for Vercel AI Gateway (stdlib only).

Jev is an evaluation model: it takes a shared `state` plus typed questions and
returns a boolean probability, a choice, or a score for each. Every caller must
treat JevUnavailable as "fall back to normal behavior".
"""
import json
import os
import urllib.error
import urllib.request

URL = os.environ.get("JEV_URL", "https://ai-gateway.vercel.sh/v1/evaluate")
MODEL = os.environ.get("JEV_MODEL", "typesafe-ai/jev")
MAX_STATE_CHARS = 90_000  # ~25k tokens; Jev caps state + longest question at 32k


class JevUnavailable(Exception):
    pass


ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def api_key():
    """Env var first, then ~/.agents/jev/.env (so hooks work in already-running sessions)."""
    key = os.environ.get("AI_GATEWAY_API_KEY")
    if key:
        return key
    try:
        with open(ENV_FILE) as f:
            for line in f:
                name, _, value = line.strip().partition("=")
                if name == "AI_GATEWAY_API_KEY" and value:
                    return value
    except OSError:
        pass
    return None


def ask(state, questions, timeout=8.0):
    """Returns {name: answer}. Boolean answers are normalized to {"p": float}."""
    key = api_key()
    if not key:
        raise JevUnavailable("AI_GATEWAY_API_KEY is not set")
    if not isinstance(state, str):
        state = json.dumps(state, ensure_ascii=False)
    if len(state) > MAX_STATE_CHARS:
        state = state[:MAX_STATE_CHARS] + "\n[... truncated ...]"
    body = json.dumps({"model": MODEL, "state": state, "questions": questions}).encode()
    req = urllib.request.Request(
        URL,
        data=body,
        method="POST",
        headers={"authorization": f"Bearer {key}", "content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise JevUnavailable(f"Jev HTTP {e.code}: {e.read()[:200]!r}") from e
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        raise JevUnavailable(f"Jev request failed: {e}") from e

    answers = data.get("answers")
    if not isinstance(answers, dict):
        raise JevUnavailable(f"Jev response missing answers: {str(data)[:200]}")
    out = {}
    for name, q in questions.items():
        a = answers.get(name)
        if not isinstance(a, dict):
            raise JevUnavailable(f"Jev gave no answer for {name}")
        if q["type"] == "boolean":
            # The gateway's field name is unverified; accept the known variants.
            p = next((a[k] for k in ("boolean", "noul", "probability", "p", "value")
                      if isinstance(a.get(k), (int, float)) and not isinstance(a.get(k), bool)), None)
            if p is None:
                raise JevUnavailable(f"Unrecognized boolean answer for {name}: {a}")
            out[name] = {"p": float(p)}
        else:
            out[name] = a
    return out


def boolean(instructions, true=None, false=None):
    q = {"type": "boolean", "instructions": instructions}
    if true or false:
        q["criteria"] = {k: v for k, v in (("true", true), ("false", false)) if v}
    return q


def choice(instructions, criteria):
    return {"type": "choice", "instructions": instructions, "criteria": criteria}


def score(instructions, criteria):
    return {"type": "score", "instructions": instructions, "criteria": criteria}


def _level(key, criteria):
    """Index of a score level given as an index, a numeric string, or a label."""
    if isinstance(key, (int, float)) and not isinstance(key, bool):
        return float(key)
    if isinstance(key, str):
        if key in criteria:
            return float(criteria.index(key))
        try:
            return float(key)
        except ValueError:
            pass
    return None


def expected_score(answer, criteria):
    """0..1 from a score answer (criteria low→high), using probabilities when present."""
    top = max(len(criteria) - 1, 1)
    probs = answer.get("probabilities") or {}
    pairs = [(_level(k, criteria), v) for k, v in probs.items()]
    pairs = [(lv, v) for lv, v in pairs if lv is not None and isinstance(v, (int, float))]
    if pairs:
        total = sum(v for _, v in pairs) or 1.0
        return sum(lv * v for lv, v in pairs) / total / top
    lv = _level(answer.get("score"), criteria)
    if lv is None:
        raise JevUnavailable(f"Unrecognized score answer: {answer}")
    return lv / top
