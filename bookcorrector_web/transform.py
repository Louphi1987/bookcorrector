from __future__ import annotations


def select_non_overlapping_issues(
    issues: list[dict[str, object]],
    selected_ids: set[str],
) -> list[dict[str, object]]:
    ordered = sorted(
        (
            issue
            for issue in issues
            if issue.get("id") in selected_ids and issue.get("replacement")
        ),
        key=lambda issue: (int(issue["start"]), int(issue["end"])),
    )
    accepted: list[dict[str, object]] = []
    for issue in ordered:
        overlaps = any(
            not (int(issue["end"]) <= int(current["start"]) or int(issue["start"]) >= int(current["end"]))
            for current in accepted
        )
        if not overlaps:
            accepted.append(issue)
    return accepted


def build_corrected_segments(
    original_text: str,
    issues: list[dict[str, object]],
    selected_ids: set[str],
) -> list[dict[str, object]]:
    accepted = select_non_overlapping_issues(issues, selected_ids)
    segments: list[dict[str, object]] = []
    cursor = 0

    for issue in accepted:
        start = int(issue["start"])
        end = int(issue["end"])
        replacement = str(issue.get("replacement") or "")
        if cursor < start:
            segments.append({"text": original_text[cursor:start], "changed": False})
        segments.append(
            {
                "text": replacement or original_text[start:end],
                "changed": bool(replacement),
                "issueId": issue["id"],
                "category": issue["category"],
            }
        )
        cursor = end

    if cursor < len(original_text):
        segments.append({"text": original_text[cursor:], "changed": False})

    return segments
