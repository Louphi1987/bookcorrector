from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class Issue:
    issue_id: str
    category: str
    message: str
    excerpt: str
    start: int
    end: int
    source: str
    suggestion: str = ""
    severity: str = "moyenne"
    confidence: float = 0.5
    replacement: str | None = None
    default_selected: bool = False

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["id"] = payload.pop("issue_id")
        return payload


@dataclass(slots=True)
class AnalysisResult:
    original_text: str
    issues: list[Issue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_payload(self, filename: str) -> dict[str, object]:
        selected_ids = [issue.issue_id for issue in self.issues if issue.default_selected]
        stats = {
            "total": len(self.issues),
            "orthographe": sum(1 for issue in self.issues if issue.category == "orthographe"),
            "grammaire": sum(1 for issue in self.issues if issue.category == "grammaire"),
            "typographie": sum(1 for issue in self.issues if issue.category == "typographie"),
            "style": sum(1 for issue in self.issues if issue.category == "style"),
        }
        return {
            "filename": filename,
            "original_text": self.original_text,
            "issues": [issue.to_dict() for issue in self.issues],
            "warnings": self.warnings,
            "selected_ids": selected_ids,
            "stats": stats,
        }
