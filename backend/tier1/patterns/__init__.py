"""Minimal pattern library for Tier 1 deterministic scanner.

Loads vulnerability pattern YAML files and evaluates deterministic
signals against indexer data. No LLM dependency — pure regex/presence
scoring at zero cost.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


# ── Schema (minimal — no LLM fields) ────────────────────────────────


class DeterministicSignal(BaseModel):
    model_config = ConfigDict(extra="allow")

    signal_type: str  # regex | dependency | file_presence
    description: str = ""
    patterns: list[str] = Field(default_factory=list)
    file_globs: list[str] = Field(default_factory=list)
    package_names: list[str] = Field(default_factory=list)
    weight: float = 1.0
    is_positive: bool = True


class VulnerabilityPattern(BaseModel):
    model_config = ConfigDict(extra="allow")  # Ignore LLM fields we don't need

    id: str
    name: str
    slug: str
    description: str = ""
    category: str = "security"
    severity_default: str = "critical"
    cwe_ids: list[str] = Field(default_factory=list)
    signals: list[DeterministicSignal] = Field(default_factory=list)
    deterministic_threshold: float = 0.7
    fix_strategy: str = ""


# ── Loader ───────────────────────────────────────────────────────────


class PatternLibrary:
    """Load and access vulnerability patterns."""

    def __init__(self, patterns: list[VulnerabilityPattern] | None = None):
        self._patterns = {p.id: p for p in (patterns or [])}

    @classmethod
    def load_from_directory(cls, directory: str | Path) -> PatternLibrary:
        directory = Path(directory)
        patterns: list[VulnerabilityPattern] = []
        for yaml_file in sorted(directory.rglob("*.yaml")):
            try:
                data = yaml.safe_load(yaml_file.read_text())
                if data and isinstance(data, dict) and "id" in data:
                    patterns.append(VulnerabilityPattern(**data))
            except Exception as exc:
                logger.warning("Skipping invalid pattern %s: %s", yaml_file, exc)
        return cls(patterns)

    @classmethod
    def load_default(cls) -> PatternLibrary:
        default_dir = Path(__file__).parent / "library" / "curated"
        if default_dir.is_dir():
            return cls.load_from_directory(default_dir)
        return cls()

    def all(self) -> list[VulnerabilityPattern]:
        return list(self._patterns.values())

    def get(self, pattern_id: str) -> VulnerabilityPattern | None:
        return self._patterns.get(pattern_id)

    def __len__(self) -> int:
        return len(self._patterns)


# ── Signal evaluator ─────────────────────────────────────────────────


def evaluate_pattern_signals(
    pattern: VulnerabilityPattern,
    *,
    signals: dict[str, list[dict]],
    dependency_names: list[str],
    all_file_paths: list[str],
) -> tuple[float, list[dict]]:
    """Evaluate a pattern's deterministic signals against indexer data.

    Returns (score, evidence_list) where score is 0.0-1.0 and
    evidence_list contains signal match details.
    """
    total_weight = sum(s.weight for s in pattern.signals) or 1.0
    achieved = 0.0
    evidence: list[dict] = []

    # Pre-compute per-signal regex matches from the indexer's pattern_signals bucket
    regex_matches = signals.get(f"pattern:{pattern.slug}", [])

    for signal in pattern.signals:
        matched = False
        match_details: list[dict] = []

        if signal.signal_type == "dependency":
            dep_lower = {d.lower() for d in dependency_names}
            for pkg in signal.package_names:
                if pkg.lower() in dep_lower:
                    matched = True
                    match_details.append({
                        "file_path": "(dependency)",
                        "line_number": None,
                        "snippet": f"Package: {pkg}",
                        "match": signal.description,
                    })

        elif signal.signal_type == "regex":
            # Regex matches were pre-computed by the indexer
            if regex_matches:
                matched = True
                match_details = regex_matches[:5]

        elif signal.signal_type == "file_presence":
            found = any(
                any(fp.startswith(p) or f"/{p}" in fp for p in signal.patterns)
                for fp in all_file_paths
            )
            if signal.is_positive:
                matched = found
            else:
                matched = not found  # Bad if ABSENT
                if matched:
                    match_details.append({
                        "file_path": "(missing)",
                        "line_number": None,
                        "snippet": f"Expected: {', '.join(signal.patterns[:3])}",
                        "match": signal.description,
                    })

        if matched:
            achieved += signal.weight
            evidence.extend(match_details[:5])

    score = achieved / total_weight
    return score, evidence


def read_dependency_names(repo_dir: str | Path) -> list[str]:
    """Extract dependency names from package.json and requirements.txt."""
    repo_dir = Path(repo_dir)
    deps: list[str] = []

    pkg_json = repo_dir / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text())
            deps.extend(data.get("dependencies", {}).keys())
            deps.extend(data.get("devDependencies", {}).keys())
        except Exception:
            pass

    req_txt = repo_dir / "requirements.txt"
    if req_txt.exists():
        for line in req_txt.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                deps.append(
                    line.split("==")[0].split(">=")[0].split("[")[0].strip()
                )

    return deps
