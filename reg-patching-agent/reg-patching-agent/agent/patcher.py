"""Step 3: propose minimal, exact-match edits per file."""
import os
from .llm import ask_json

SYSTEM = """You update bank compliance logic. Rules:
- Make the SMALLEST change that satisfies the cited obligations.
- Never touch unrelated code, auth, or secrets. Never add network calls.
- Express changes as exact-match edits; 'old' must appear exactly once in the file.
- If the file needs no change or the requirement is ambiguous, return no edits and say why.
- Update inline comments/docs with the regulation citation and effective date.
Return ONLY JSON."""

TEMPLATE = """Regulatory change: {title} ({url}); effective {effective}

Obligations to satisfy:
{obligations}

File: {path}
-----
{content}
-----
Return JSON: {{"edits":[{{"old":"...","new":"..."}}], "rationale":"...", "needs_human":bool, "open_questions":["..."]}}"""


def propose(model, doc, effective, obligations, path, content):
    return ask_json(model, SYSTEM, TEMPLATE.format(
        title=doc["title"], url=doc["url"], effective=effective,
        obligations="\n".join(f"- {o['id']} [{o.get('citation')}]: {o['requirement']} {o.get('parameters')}"
                              for o in obligations),
        path=path, content=content))


def apply_edits(repo_root, path, edits):
    full = os.path.join(repo_root, path)
    text = open(full, encoding="utf-8").read()
    for e in edits:
        if text.count(e["old"]) != 1:
            return False, f"edit target not unique/found in {path}"
        text = text.replace(e["old"], e["new"])
    open(full, "w", encoding="utf-8").write(text)
    return True, "ok"
