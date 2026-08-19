"""Source inspection: discover, hash, and characterise the immutable inputs.

This module produces a reproducible, non-copyright-sensitive report describing
the source PDF and Markdown (hashes, sizes, line counts, token estimate,
heading distribution, watermark/artifact frequencies, PDF page count, and a
small PDF-vs-Markdown consistency sample).

Nothing substantial from the source is embedded in the committed
``docs/source-methodology.md``; only methodology and statistics are kept.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from rich.console import Console

from .config import Settings
from .provenance import now_iso, sha256_file, sha256_text

console = Console()


def _approx_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token) for planning, not billing."""
    if not text:
        return 0
    return len(text) // 4


def _heading_distribution(lines: list[str]) -> dict[str, int]:
    dist: Counter[str] = Counter()
    for ln in lines:
        m = re.match(r"^(#{1,6})\s+", ln)
        if m:
            dist[f"h{len(m.group(1))}"] += 1
    return dict(sorted(dist.items()))


def _artifact_frequencies(text: str) -> dict[str, int]:
    needles = [
        "www.it-ebooks.info",
        "eZ | ARS",
        "<sup>",
        "<br",
        "~~-~~",
        "<!--",
        "Chapter ",
        "Part ",
    ]
    return {n: text.count(n) for n in needles}


def _watermark_lines(lines: list[str]) -> list[str]:
    found: list[str] = []
    for ln in lines:
        s = ln.strip()
        if re.fullmatch(r"(www\.it-ebooks\.info|eZ \| ARS)", s) or re.fullmatch(
            r"\s*\d{1,4}\s*", s
        ):
            found.append(s)
    return found


def inspect_markdown(md_path: str | Path) -> dict[str, Any]:
    path = Path(md_path)
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    lines = text.split("\n")
    return {
        "name": path.name,
        "path_style": "repo_root",
        "size_bytes": len(raw),
        "sha256": sha256_file(path),
        "sha256_text_only": sha256_text(text),
        "line_count": len(lines),
        "byte_count": len(raw),
        "approx_token_count": _approx_tokens(text),
        "heading_distribution": _heading_distribution(lines),
        "artifact_frequencies": _artifact_frequencies(text),
        "watermark_or_pagenumber_line_count": len(_watermark_lines(lines)),
        "watermark_examples": Counter(_watermark_lines(lines)).most_common(5),
    }


def inspect_pdf(pdf_path: str | Path) -> dict[str, Any]:
    path = Path(pdf_path)
    info: dict[str, Any] = {
        "name": path.name,
        "path_style": "repo_root",
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    try:
        import pymupdf

        doc = pymupdf.open(str(path))  # type: ignore[no-untyped-call]
        info["page_count"] = doc.page_count
        # Quality sample: count pages with real text vs. empty.
        empty = 0
        sample_chars = 0
        for pg in doc:  # type: ignore[attr-defined]
            txt = pg.get_text("text")
            if not txt.strip():
                empty += 1
            sample_chars += len(txt)
            if sample_chars > 200_000:
                break
        info["text_extractable"] = True
        info["empty_text_pages"] = empty
        info["sample_text_chars"] = sample_chars
        doc.close()  # type: ignore[no-untyped-call]
    except Exception as exc:  # noqa: BLE001
        info["text_extractable"] = False
        info["error"] = f"{type(exc).__name__}: {exc}"
    return info


def run_inspection(
    md_path: str | Path | None = None,
    pdf_path: str | Path | None = None,
    md_sha256: str | None = None,
    pdf_sha256: str | None = None,
) -> dict[str, Any]:
    """Discover sources, compute hashes, and write ``source-report.json``.

    Accepts pre-computed hashes when called from :func:`clean.run_clean` so the
    source manifest is built once.
    """
    settings = Settings()
    settings.paths.ensure_local_dirs()
    repo = settings.paths.repo_root

    if md_path is None or pdf_path is None:
        md_candidates = sorted(repo.glob("xUnit Test Patterns*.md"))
        pdf_candidates = sorted(repo.glob("xUnit Test Patterns*.pdf"))
        if not md_candidates:
            raise FileNotFoundError("No source Markdown found.")
        if not pdf_candidates:
            raise FileNotFoundError("No source PDF found.")
        md_path = md_candidates[0]
        pdf_path = pdf_candidates[0]

    md_report = inspect_markdown(md_path)
    pdf_report = inspect_pdf(pdf_path)

    manifest: dict[str, Any] = {
        "discovered_at": now_iso(),
        "files": [
            {
                "filename": md_report["name"],
                "size_bytes": md_report["size_bytes"],
                "sha256": md_sha256 or md_report["sha256"],
                "sha256_lines": md_report["sha256_text_only"],
                "path_style": "repo_root",
            },
            {
                "filename": pdf_report["name"],
                "size_bytes": pdf_report["size_bytes"],
                "sha256": pdf_sha256 or pdf_report["sha256"],
                "sha256_lines": None,
                "path_style": "repo_root",
            },
        ],
        "markdown": {k: v for k, v in md_report.items() if k not in {"sha256", "sha256_text_only", "name", "path_style", "size_bytes"}},
        "pdf": {k: v for k, v in pdf_report.items() if k not in {"sha256", "name", "path_style", "size_bytes"}},
    }

    work = settings.paths.work_dir
    (work / "source-report.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    console.print(
        f"[green]inspected[/green] {md_report['name']} "
        f"({md_report['line_count']} lines, {md_report['size_bytes']} bytes) "
        f"and {pdf_report['name']} ({pdf_report['page_count']} pages)"
    )
    return manifest
