"""Stage 9: package the Agent Skill into a reproducible manifest artifact.

`run_bundle` writes `skill/agentic-testcraft/.skill-manifest.json` listing every
committed skill file with size + sha256, records the front-matter version/status,
and then runs the Stage-9 validator so packaging = packaging + gating. This is
the M9 "dist artifact" step from the architecture table.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .config import load_settings
from .skill_validate import load_front_matter, run_validate_skill


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_record(path: Path, skill_dir: Path) -> dict[str, object]:
    return {
        "path": str(path.relative_to(skill_dir)),
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "lines": path.read_text(encoding="utf-8").count("\n") + 1,
    }


def run_bundle(skill_dir: Path | None = None) -> dict[str, object]:
    settings = load_settings()
    if skill_dir is None:
        skill_dir = settings.paths.skill_dir
    skill_dir = Path(skill_dir)
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        raise FileNotFoundError(f"no SKILL.md under {skill_dir}")

    fm = load_front_matter(skill_md.read_text(encoding="utf-8"))
    files = [
        _file_record(p, skill_dir)
        for p in sorted(skill_dir.rglob("*"))
        if p.is_file() and p.name != ".skill-manifest.json"
    ]

    manifest: dict[str, object] = {
        "name": "agentic-testcraft",
        "version": fm.get("version", "0.0.0"),
        "status": fm.get("status", "wip"),
        "title": fm.get("title", ""),
        "evidence_base": fm.get("evidence_base", ""),
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "file_count": len(files),
        "files": files,
    }
    out = skill_dir / ".skill-manifest.json"
    out.write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )

    report = run_validate_skill(skill_dir=skill_dir)
    report["manifest"] = str(out)
    report["file_count"] = len(files)
    return report


def main() -> None:
    report = run_bundle()
    print(
        f"ok: bundled {report['file_count']} files -> {report['manifest']} "
        f"({report['title']} v{report['version']}, {report['status']})"
    )


if __name__ == "__main__":
    main()
