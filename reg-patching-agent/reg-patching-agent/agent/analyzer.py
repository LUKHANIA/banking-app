"""Step 1: decide whether a regulatory document matters and extract obligations."""
from .llm import ask_json

SYSTEM = """You are a regulatory analyst for a retail/commercial bank's engineering team.
Return ONLY JSON. Be conservative: never invent requirements; quote section references
only if present in the text. If the document does not change obligations that software
or documentation must reflect, set relevant=false."""

TEMPLATE = """Topics the bank's code covers: {topics}

Document: {title}
Source: {source} | URL: {url} | Effective: {effective}

Text:
{text}

Return JSON:
{{"relevant": bool,
  "summary": "2-3 sentences",
  "effective_date": "YYYY-MM-DD or null",
  "confidence": 0.0-1.0,
  "obligations": [{{"id":"OB-1","topic":"one of the topics","requirement":"...",
                    "citation":"section ref or null",
                    "parameters":{{"name":"new value, e.g. threshold, deadline"}},
                    "keywords":["identifiers likely in code"]}}]}}"""


def analyze(model, doc, text, topics):
    return ask_json(model, SYSTEM, TEMPLATE.format(
        topics=", ".join(topics), title=doc["title"], source=doc["source"],
        url=doc["url"], effective=doc.get("effective_on"), text=text))
