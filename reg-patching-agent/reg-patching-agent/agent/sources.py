"""Fetch new regulatory documents from configured sources."""
import datetime as dt
import hashlib
import xml.etree.ElementTree as ET
import requests

FR_API = "https://www.federalregister.gov/api/v1/documents.json"


def _since(days):
    return (dt.date.today() - dt.timedelta(days=days)).isoformat()


def fetch_federal_register(src, days):
    params = {
        "conditions[agencies][]": src["agency"],
        "conditions[type][]": ["RULE", "PRORULE", "NOTICE"],
        "conditions[publication_date][gte]": _since(days),
        "fields[]": ["document_number", "title", "abstract", "html_url",
                     "effective_on", "publication_date", "full_text_xml_url"],
        "per_page": 50,
    }
    r = requests.get(FR_API, params=params, timeout=30)
    r.raise_for_status()
    return [{
        "id": f"{src['name']}-{d['document_number']}",
        "source": src["name"],
        "title": d["title"],
        "abstract": d.get("abstract") or "",
        "url": d["html_url"],
        "effective_on": d.get("effective_on"),
        "published": d["publication_date"],
        "text_url": d.get("full_text_xml_url"),
    } for d in r.json().get("results", [])]


def fetch_rss(src, days):
    r = requests.get(src["url"], timeout=30)
    r.raise_for_status()
    out = []
    for item in ET.fromstring(r.content).iter("item"):
        link = (item.findtext("link") or "").strip()
        out.append({
            "id": f"{src['name']}-{hashlib.sha1(link.encode()).hexdigest()[:10]}",
            "source": src["name"],
            "title": (item.findtext("title") or "").strip(),
            "abstract": (item.findtext("description") or "").strip(),
            "url": link,
            "effective_on": None,
            "published": item.findtext("pubDate"),
            "text_url": None,
        })
    return out


def fetch_full_text(doc, limit=40000):
    if not doc.get("text_url"):
        return doc["abstract"]
    try:
        r = requests.get(doc["text_url"], timeout=30)
        r.raise_for_status()
        return r.text[:limit]
    except requests.RequestException:
        return doc["abstract"]


def fetch_all(cfg):
    docs = []
    for src in cfg["sources"]:
        try:
            fn = fetch_federal_register if src["type"] == "federal_register" else fetch_rss
            docs += fn(src, cfg["lookback_days"])
        except Exception as e:  # one failing feed must not block the others
            print(f"[warn] {src['name']} failed: {e}")
    return docs
