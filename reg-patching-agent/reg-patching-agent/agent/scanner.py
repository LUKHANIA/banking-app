"""Step 2: locate affected files via compliance-map.yml + keyword search."""
import os, re, yaml


def _ok(path, cfg):
    p = path.replace("\\", "/")
    if any(p.startswith(d) for d in cfg["denied_paths"]):
        return False
    return any(p.startswith(a) for a in cfg["allowed_paths"])


def _walk(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".venv"}]
        for f in files:
            yield os.path.relpath(os.path.join(base, f), root)


def find_affected(repo_root, cfg, obligations):
    cmap = yaml.safe_load(open(os.path.join(repo_root, "compliance-map.yml")))["topics"]
    hits = {}  # path -> set(obligation ids)
    all_files = [p for p in _walk(repo_root) if _ok(p, cfg)]

    for ob in obligations:
        topic = cmap.get(ob["topic"], {})
        for p in all_files:  # a) mapped paths
            if any(p.startswith(m) for m in topic.get("paths", [])):
                hits.setdefault(p, set()).add(ob["id"])
        # b) keyword search (mapped keywords + LLM-suggested ones)
        kws = set(topic.get("keywords", [])) | set(ob.get("keywords", []))
        if not kws:
            continue
        pat = re.compile("|".join(re.escape(k) for k in kws), re.I)
        for p in all_files:
            full = os.path.join(repo_root, p)
            if os.path.getsize(full) > cfg["max_file_bytes"]:
                continue
            try:
                if pat.search(open(full, encoding="utf-8").read()):
                    hits.setdefault(p, set()).add(ob["id"])
            except (UnicodeDecodeError, OSError):
                continue

    ranked = sorted(hits.items(), key=lambda kv: -len(kv[1]))[: cfg["max_files_per_pr"]]
    return {p: sorted(ids) for p, ids in ranked}
