import json, re
import anthropic

_client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY


def ask_json(model, system, user, max_tokens=4000):
    msg = _client.messages.create(
        model=model, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in msg.content if b.type == "text")
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text)
