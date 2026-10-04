#!/usr/bin/env python3
"""Publish the numbered plan tickets as GitHub issues with gh.

Dry run by default. Re-running --publish skips issues with matching plan IDs.
"""

import argparse
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "plan-doc.md"
REPO = "RyanSmith19/mlb-analyzer"
HEADING = re.compile(r"^(## Epic |### )(MLB-\d+): (.+)$")
INLINE_LABEL = re.compile(r"`([^`]+)`")
COLORS = {
    "epic": "5319e7",
    "story": "1d76db",
    "task": "0e8a16",
    "spike": "fbca04",
    "P0": "b60205",
    "P1": "d93f0b",
    "P2": "fbca04",
    "P3": "c2e0c6",
}


@dataclass
class Issue:
    plan_id: str
    title: str
    body: str
    labels: list[str]
    parent_id: str | None


def gh(*args: str) -> str:
    return subprocess.check_output(["gh", *args], text=True).strip()


def parse_plan() -> list[Issue]:
    lines = PLAN.read_text(encoding="utf-8").splitlines()
    sections: list[tuple[str, str, bool, str | None, list[str]]] = []
    current: tuple[str, str, bool, str | None, list[str]] | None = None
    parent_id: str | None = None

    for line in lines:
        match = HEADING.match(line)
        if match:
            if current:
                sections.append(current)
            kind, plan_id, title = match.groups()
            is_epic = kind == "## Epic "
            if is_epic:
                parent_id = plan_id
            current = (plan_id, title, is_epic, None if is_epic else parent_id, [])
        elif current and (line == "---" or line.startswith("# ")):
            sections.append(current)
            current = None
        elif current:
            current[4].append(line)
    if current:
        sections.append(current)

    issues: list[Issue] = []
    for plan_id, title, is_epic, parent_id, content in sections:
        body = "\n".join(content).strip()
        labels = ["epic" if is_epic else "story"]
        type_match = re.search(r"^Issue type: `([^`]+)`", body, re.MULTILINE)
        if type_match and not is_epic:
            labels[0] = type_match.group(1).lower()
        priority_match = re.search(r"^Priority: `(P[0-3])`", body, re.MULTILINE)
        if priority_match:
            labels.append(priority_match.group(1))
        label_match = re.search(r"^Labels: (.+)$", body, re.MULTILINE)
        if label_match:
            labels.extend(INLINE_LABEL.findall(label_match.group(1)))
        issues.append(Issue(plan_id, title, body, list(dict.fromkeys(labels)), parent_id))

    ids = [issue.plan_id for issue in issues]
    if len(ids) != len(set(ids)) or len(ids) != 87:
        raise ValueError(f"Expected 87 unique plan IDs, found {len(ids)}")
    return issues


def existing_issues() -> dict[str, int]:
    data = json.loads(gh("issue", "list", "-R", REPO, "--state", "all", "--limit", "1000", "--json", "number,title,body"))
    result = {}
    for issue in data:
        title_id = re.match(r"^\[(MLB-\d+)\]", issue["title"])
        body_id = re.search(r"^Plan ID: (MLB-\d+)$", issue.get("body") or "", re.MULTILINE)
        for match in (title_id, body_id):
            if match:
                result[match.group(1)] = issue["number"]
    return result


def ensure_labels(issues: list[Issue]) -> None:
    data = json.loads(gh("label", "list", "-R", REPO, "--limit", "1000", "--json", "name"))
    existing = {item["name"] for item in data}
    for label in sorted({label for issue in issues for label in issue.labels} - existing):
        gh("label", "create", label, "-R", REPO, "--color", COLORS.get(label, "ededed"))
        print(f"Created label: {label}", flush=True)


def publish(issues: list[Issue]) -> None:
    existing = existing_issues()
    ensure_labels(issues)
    for issue in issues:
        if issue.plan_id in existing:
            print(f"Skipped {issue.plan_id}: already #{existing[issue.plan_id]}", flush=True)
            continue
        body = f"Plan ID: {issue.plan_id}\n\n"
        if issue.parent_id and issue.parent_id in existing:
            body += f"Parent epic: #{existing[issue.parent_id]}\n\n"
        body += issue.body + "\n"
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".md") as file:
            file.write(body)
            file.flush()
            args = ["issue", "create", "-R", REPO, "--title", f"[{issue.plan_id}] {issue.title}", "--body-file", file.name]
            for label in issue.labels:
                args.extend(["--label", label])
            url = gh(*args)
        match = re.search(r"/(\d+)$", url)
        if not match:
            raise ValueError(f"Unexpected gh issue URL: {url}")
        existing[issue.plan_id] = int(match.group(1))
        print(f"Created {issue.plan_id}: {url}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true", help="Create missing GitHub issues")
    args = parser.parse_args()
    issues = parse_plan()
    if args.publish:
        publish(issues)
    else:
        for issue in issues:
            print(f"{issue.plan_id}: {issue.title} [{', '.join(issue.labels)}]")
        print(f"Prepared {len(issues)} issues. Pass --publish to create them.")


if __name__ == "__main__":
    main()
