"""Regulatory Patching Agent — entrypoint.

Usage: python -m agent.main [--dry-run] [--doc-url URL]
"""
import argparse, json, os, sys, yaml
from . import sources, analyzer, scanner, patcher, github_pr as gh

ROOT = os.getcwd()


def audit(entry):
    os.makedirs("audit", exist_ok=True)
    with open("audit/agent-log.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def process(doc, cfg, topics, repo, base, dry_run):
    branch = f"reg-patch/{doc['id'].lower().replace(' ', '-')}"[:80]
    if not dry_run and gh.branch_exists(repo, branch):
        print(f"[skip] {doc['id']} already has a branch")
        return
    text = sources.fetch_full_text(doc)
    analysis = analyzer.analyze(cfg["model"], doc, text, topics)
    audit({"doc": doc["id"], "relevant": analysis["relevant"], "confidence": analysis.get("confidence")})
    if not analysis["relevant"] or analysis.get("confidence", 0) < 0.5:
        print(f"[skip] {doc['id']} not relevant/low confidence")
        return

    obs = {o["id"]: o for o in analysis["obligations"]}
    affected = scanner.find_affected(ROOT, cfg, analysis["obligations"])
    print(f"[info] {doc['id']}: {len(affected)} candidate files")

    results, changed = {}, []
    for path, ids in affected.items():
        content = open(os.path.join(ROOT, path), encoding="utf-8").read()
        prop = patcher.propose(cfg["model"], doc, analysis.get("effective_date"),
                               [obs[i] for i in ids], path, content)
        if not prop["edits"]:
            continue
        if dry_run:
            print(f"[dry-run] {path}: {prop['rationale']}")
            continue
        ok, msg = patcher.apply_edits(ROOT, path, prop["edits"])
        if not ok:
            print(f"[warn] {msg}")
            continue
        changed.append(path)
        results[path] = {"ids": ids, "rationale": prop["rationale"],
                         "open_questions": prop.get("open_questions", [])}

    if not changed:
        return
    tests_ok, log = gh.run_tests(cfg["test_command"])
    title = f"[Reg Patch] {doc['source']}: {doc['title'][:80]}"
    body = gh.render_body(doc, analysis, results, tests_ok, log)
    url = gh.open_pr(repo, base, branch, title, body, cfg, changed, doc["id"])
    audit({"doc": doc["id"], "pr": url, "files": changed, "tests_ok": tests_ok})
    print(f"[done] {url}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--doc-url")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "config.yaml")))
    topics = list(yaml.safe_load(open("compliance-map.yml"))["topics"])
    repo, base = os.environ["GITHUB_REPOSITORY"], os.environ.get("BASE_BRANCH", "main")

    docs = sources.fetch_all(cfg)
    if args.doc_url:
        docs = [d for d in docs if d["url"] == args.doc_url]
    print(f"[info] {len(docs)} documents to evaluate")
    for d in docs:
        try:
            process(d, cfg, topics, repo, base, args.dry_run)
        except Exception as e:
            print(f"[error] {d['id']}: {e}")
            audit({"doc": d["id"], "error": str(e)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
