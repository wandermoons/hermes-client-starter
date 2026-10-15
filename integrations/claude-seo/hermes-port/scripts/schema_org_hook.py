#!/usr/bin/env python3
"""Dwight post-render Schema.org validation hook.

The hook either validates local raw/rendered HTML fixtures or performs one
bounded render through Claude SEO's hardened renderer. It always writes a
compact render summary and a structured Schema.org validation artifact.
It never changes the audited site.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

VALIDATOR = "dwight-schema-org-hook"
VALIDATOR_VERSION = "1.0.0"
MAX_BLOCKS = 100
MAX_BLOCK_BYTES = 1 * 1024 * 1024
MAX_TOTAL_BYTES = 5 * 1024 * 1024
MAX_NODES = 10_000
MAX_DEPTH = 50
MAX_INVALID_RAW_CHARS = 4_096

RETIRED_GOOGLE_TYPES = {
    "HowTo": "Google rich results removed September 2023",
    "SpecialAnnouncement": "Google rich results deprecated July 31, 2025",
    "CourseInfo": "Google rich results retired June 2025",
    "EstimatedSalary": "Google rich results retired June 2025",
    "LearningVideo": "Google rich results retired June 2025",
    "ClaimReview": "Google fact-check rich results retired June 2025",
    "VehicleListing": "Google vehicle listing rich results retired June 2025",
    "PracticeProblem": "Google Search support removed January 6, 2026",
    "Book": "Google Book Actions rich-result support retired",
}

PLACEHOLDER_PATTERNS = (
    re.compile(r"\[[^\]]*(?:name|city|state|phone|address|url|email|insert|your)[^\]]*\]", re.I),
    re.compile(r"\b(?:replace[_ -]?me|todo|lorem ipsum)\b", re.I),
)

URL_PROPERTIES = {
    "@id",
    "url",
    "sameAs",
    "image",
    "logo",
    "contentUrl",
    "embedUrl",
    "thumbnailUrl",
    "mainEntityOfPage",
    "availability",
}
DATE_PROPERTIES = {
    "datePublished",
    "dateModified",
    "startDate",
    "endDate",
    "uploadDate",
}
RECOMMENDED_PROPERTIES = {
    "Organization": ("name", "url"),
    "WebSite": ("name", "url"),
    "WebPage": ("name",),
    "Article": ("headline", "author", "datePublished"),
    "BlogPosting": ("headline", "author", "datePublished"),
    "NewsArticle": ("headline", "author", "datePublished"),
    "Product": ("name", "image", "offers"),
    "LocalBusiness": ("name", "address"),
    "BreadcrumbList": ("itemListElement",),
}
SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


class JsonLdHTMLParser(HTMLParser):
    """Extract JSON-LD scripts regardless of attribute order or extra attrs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.blocks: list[str] = []
        self._capturing = False
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        attr_map = {str(key).lower(): str(value or "") for key, value in attrs}
        if attr_map.get("type", "").strip().lower() == "application/ld+json":
            self._capturing = True
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._capturing:
            self._parts.append(data)

    def handle_entityref(self, name: str) -> None:
        if self._capturing:
            self._parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self._capturing:
            self._parts.append(f"&#{name};")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._capturing:
            self.blocks.append("".join(self._parts).strip())
            self._capturing = False
            self._parts = []


class Findings:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def add(
        self,
        code: str,
        severity: str,
        message: str,
        *,
        source: str,
        block_index: int | None = None,
        pointer: str = "",
        rule_source: str = "Schema.org / local validation policy",
    ) -> None:
        evidence_pointer = pointer or ""
        block_segment = f"/blocks/{block_index - 1}" if block_index else ""
        self.items.append(
            {
                "code": code,
                "severity": severity,
                "message": message,
                "source": source,
                "block_index": block_index,
                "json_pointer": pointer,
                "evidence_id": f"schema-validation.json#/{source}{block_segment}{evidence_pointer}",
                "rule_source": rule_source,
            }
        )

    def sorted(self) -> list[dict[str, Any]]:
        return sorted(
            self.items,
            key=lambda item: (
                SEVERITY_ORDER[item["severity"]],
                item["code"],
                item.get("block_index") or 0,
                item.get("json_pointer") or "",
            ),
        )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pointer_escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _is_absolute_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _valid_iso_date(value: str) -> bool:
    candidate = value.strip()
    if not candidate:
        return False
    try:
        datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        return True
    except ValueError:
        try:
            datetime.strptime(candidate, "%Y-%m-%d")
            return True
        except ValueError:
            return False


def _walk(value: Any, pointer: str = "", depth: int = 0):
    """Yield bounded JSON values with RFC 6901-like pointers."""
    stack: list[tuple[Any, str, int]] = [(value, pointer, depth)]
    visited = 0
    while stack:
        current, current_pointer, current_depth = stack.pop()
        visited += 1
        if visited > MAX_NODES or current_depth > MAX_DEPTH:
            return
        yield current, current_pointer
        if isinstance(current, dict):
            for key, child in reversed(list(current.items())):
                child_pointer = f"{current_pointer}/{_pointer_escape(str(key))}"
                stack.append((child, child_pointer, current_depth + 1))
        elif isinstance(current, list):
            for index in range(len(current) - 1, -1, -1):
                stack.append((current[index], f"{current_pointer}/{index}", current_depth + 1))


def _schema_entities(data: Any) -> list[tuple[dict[str, Any], str]]:
    """Return top-level and nested typed entities without duplicates."""
    entities: list[tuple[dict[str, Any], str]] = []
    seen: set[int] = set()

    def add_entity(value: Any, pointer: str) -> None:
        if isinstance(value, dict) and id(value) not in seen:
            seen.add(id(value))
            entities.append((value, pointer))

    if isinstance(data, dict):
        if isinstance(data.get("@graph"), list):
            for index, item in enumerate(data["@graph"]):
                add_entity(item, f"/@graph/{index}")
        else:
            add_entity(data, "")
    elif isinstance(data, list):
        for index, item in enumerate(data):
            add_entity(item, f"/{index}")

    for value, pointer in _walk(data):
        if isinstance(value, dict) and "@type" in value:
            add_entity(value, pointer)
    return entities


def _types_for_entity(entity: dict[str, Any]) -> list[str]:
    value = entity.get("@type")
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _validate_entity(
    entity: dict[str, Any],
    *,
    source: str,
    block_index: int,
    pointer: str,
    findings: Findings,
) -> list[str]:
    types = _types_for_entity(entity)
    if "@type" not in entity:
        findings.add(
            "missing_type",
            "error",
            "Schema entity is missing @type.",
            source=source,
            block_index=block_index,
            pointer=pointer or "/data",
        )
    elif not types:
        findings.add(
            "invalid_type",
            "error",
            "@type must be a non-empty string or list of strings.",
            source=source,
            block_index=block_index,
            pointer=f"{pointer}/@type",
        )

    for schema_type in types:
        if schema_type in RETIRED_GOOGLE_TYPES:
            findings.add(
                "google_rich_result_retired",
                "warning",
                f"{schema_type}: {RETIRED_GOOGLE_TYPES[schema_type]}. The type may remain valid Schema.org markup but no longer receives that Google rich result.",
                source=source,
                block_index=block_index,
                pointer=f"{pointer}/@type",
                rule_source="Google Search structured-data support policy",
            )
        for prop in RECOMMENDED_PROPERTIES.get(schema_type, ()):
            if prop not in entity:
                findings.add(
                    "missing_recommended_property",
                    "warning",
                    f"{schema_type} is missing recommended property {prop!r}.",
                    source=source,
                    block_index=block_index,
                    pointer=pointer or "/data",
                    rule_source="Local rich-result readiness policy",
                )

    for value, child_pointer in _walk(entity, pointer):
        if isinstance(value, str):
            for pattern in PLACEHOLDER_PATTERNS:
                if pattern.search(value):
                    findings.add(
                        "placeholder_text",
                        "warning",
                        f"Placeholder-like text detected: {value[:120]!r}.",
                        source=source,
                        block_index=block_index,
                        pointer=child_pointer,
                    )
                    break
        if not isinstance(value, dict):
            continue
        for key, candidate in value.items():
            property_pointer = f"{child_pointer}/{_pointer_escape(str(key))}"
            if key in URL_PROPERTIES:
                url_values = candidate if isinstance(candidate, list) else [candidate]
                for url_value in url_values:
                    if isinstance(url_value, str) and not _is_absolute_url(url_value):
                        findings.add(
                            "relative_url",
                            "warning",
                            f"Property {key!r} should use an absolute HTTP(S) URL: {url_value!r}.",
                            source=source,
                            block_index=block_index,
                            pointer=property_pointer,
                        )
            if key in DATE_PROPERTIES and isinstance(candidate, str) and not _valid_iso_date(candidate):
                findings.add(
                    "invalid_date",
                    "warning",
                    f"Property {key!r} is not a valid ISO-8601 date/date-time: {candidate!r}.",
                    source=source,
                    block_index=block_index,
                    pointer=property_pointer,
                )
    return types


def extract_and_validate(html: str, source: str, findings: Findings) -> dict[str, Any]:
    parser = JsonLdHTMLParser()
    parser.feed(html or "")
    result: dict[str, Any] = {
        "block_count": len(parser.blocks),
        "processed_count": 0,
        "total_bytes": 0,
        "truncated": False,
        "types": [],
        "blocks": [],
    }
    all_types: set[str] = set()

    for zero_index, raw in enumerate(parser.blocks):
        block_index = zero_index + 1
        if zero_index >= MAX_BLOCKS:
            result["truncated"] = True
            findings.add(
                "block_limit_exceeded",
                "error",
                f"More than {MAX_BLOCKS} JSON-LD blocks were found; remaining blocks were not validated.",
                source=source,
            )
            break
        size_bytes = len(raw.encode("utf-8"))
        if result["total_bytes"] + size_bytes > MAX_TOTAL_BYTES:
            result["truncated"] = True
            findings.add(
                "total_size_limit_exceeded",
                "error",
                "Total JSON-LD byte limit exceeded; remaining blocks were not validated.",
                source=source,
                block_index=block_index,
            )
            break
        result["total_bytes"] += size_bytes
        result["processed_count"] += 1
        entry: dict[str, Any] = {
            "index": block_index,
            "size_bytes": size_bytes,
            "sha256": _sha256_text(raw),
        }
        if size_bytes > MAX_BLOCK_BYTES:
            entry.update({"valid_json": None, "data": None})
            result["truncated"] = True
            findings.add(
                "block_size_limit_exceeded",
                "error",
                f"JSON-LD block exceeds {MAX_BLOCK_BYTES} bytes and was not parsed.",
                source=source,
                block_index=block_index,
            )
            result["blocks"].append(entry)
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, RecursionError) as exc:
            entry.update(
                {
                    "valid_json": False,
                    "data": None,
                    "raw_preview": raw[:MAX_INVALID_RAW_CHARS],
                    "parse_error": f"{type(exc).__name__}: {exc}",
                }
            )
            findings.add(
                "invalid_json",
                "error",
                f"Invalid JSON-LD syntax: {exc}",
                source=source,
                block_index=block_index,
            )
            result["blocks"].append(entry)
            continue

        entry.update({"valid_json": True, "data": data})
        roots = data if isinstance(data, list) else [data]
        for root_index, root in enumerate(roots):
            root_pointer = f"/{root_index}" if isinstance(data, list) else ""
            if not isinstance(root, dict):
                findings.add(
                    "invalid_root",
                    "error",
                    "Each JSON-LD root must be an object.",
                    source=source,
                    block_index=block_index,
                    pointer=root_pointer,
                )
                continue
            context = root.get("@context")
            if context is None:
                findings.add(
                    "missing_context",
                    "error",
                    "JSON-LD root is missing @context.",
                    source=source,
                    block_index=block_index,
                    pointer=root_pointer or "/data",
                )
            elif context not in ("https://schema.org", "http://schema.org"):
                findings.add(
                    "invalid_context",
                    "error",
                    "@context must be https://schema.org (http://schema.org is tolerated).",
                    source=source,
                    block_index=block_index,
                    pointer=f"{root_pointer}/@context",
                )

        entities = _schema_entities(data)
        if not entities:
            findings.add(
                "missing_type",
                "error",
                "JSON-LD block contains no schema entity with @type.",
                source=source,
                block_index=block_index,
            )
        for entity, pointer in entities:
            all_types.update(
                _validate_entity(
                    entity,
                    source=source,
                    block_index=block_index,
                    pointer=pointer,
                    findings=findings,
                )
            )
        entry["entity_count"] = len(entities)
        entry["types"] = sorted({item for entity, _ in entities for item in _types_for_entity(entity)})
        result["blocks"].append(entry)

    result["types"] = sorted(all_types)
    result["entity_count"] = sum(int(block.get("entity_count", 0)) for block in result["blocks"])
    return result


def _render_summary(
    *,
    target_url: str,
    final_url: str,
    mode_requested: str,
    mode_used: str,
    status_code: int | None,
    is_spa: bool | None,
    render_engine: str | None,
    raw_html: str,
    rendered_html: str,
    diagnostics: list[str] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "collector": VALIDATOR,
        "target_url": target_url,
        "final_url": final_url,
        "mode_requested": mode_requested,
        "mode_used": mode_used,
        "status_code": status_code,
        "is_spa": is_spa,
        "render_engine": render_engine,
        "raw_content_bytes": len(raw_html.encode("utf-8")),
        "raw_content_sha256": _sha256_text(raw_html),
        "content_bytes": len(rendered_html.encode("utf-8")),
        "content_sha256": _sha256_text(rendered_html),
        "render_diagnostics": diagnostics or [],
        "error": error,
        "production_mutations": [],
        "paid_calls": [],
    }


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    if path.parent.is_symlink():
        raise RuntimeError(f"Refusing symlink evidence directory: {path.parent}")
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def build_artifacts(
    *,
    target_url: str,
    raw_html: str,
    rendered_html: str,
    final_url: str,
    mode_requested: str,
    mode_used: str,
    status_code: int | None,
    is_spa: bool | None,
    render_engine: str | None,
    diagnostics: list[str] | None = None,
    render_error: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    findings = Findings()
    raw_result = extract_and_validate(raw_html, "raw", findings)
    rendered_result = extract_and_validate(rendered_html, "rendered", findings)

    raw_types = set(raw_result["types"])
    rendered_types = set(rendered_result["types"])
    rendered_only_types = sorted(rendered_types - raw_types)
    javascript_injected = (
        rendered_result["block_count"] > raw_result["block_count"]
        or bool(rendered_only_types)
    )
    if javascript_injected:
        findings.add(
            "javascript_injected_schema",
            "info",
            "Rendered DOM contains JSON-LD not present in the initial HTML. For time-sensitive markup, prefer server-rendered JSON-LD.",
            source="render_comparison",
            rule_source="Google JavaScript SEO guidance / local comparison",
        )
    if render_error:
        findings.add(
            "render_error",
            "warning" if rendered_html else "error",
            f"Renderer reported: {render_error}",
            source="render_comparison",
        )

    ordered_findings = findings.sorted()
    errors = sum(item["severity"] == "error" for item in ordered_findings)
    warnings = sum(item["severity"] == "warning" for item in ordered_findings)
    infos = sum(item["severity"] == "info" for item in ordered_findings)
    block_count = rendered_result["block_count"]
    truncated = bool(raw_result["truncated"] or rendered_result["truncated"])
    if block_count == 0 and errors == 0 and not render_error:
        status = "not_found"
        valid: bool | None = None
    elif errors:
        status = "invalid"
        valid = False
    elif truncated or render_error:
        status = "partial"
        valid = None
    else:
        status = "valid"
        valid = True

    render_payload = _render_summary(
        target_url=target_url,
        final_url=final_url,
        mode_requested=mode_requested,
        mode_used=mode_used,
        status_code=status_code,
        is_spa=is_spa,
        render_engine=render_engine,
        raw_html=raw_html,
        rendered_html=rendered_html,
        diagnostics=diagnostics,
        error=render_error,
    )
    schema_payload = {
        "schema_version": 1,
        "validator": VALIDATOR,
        "validator_version": VALIDATOR_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_url": target_url,
        "final_url": final_url,
        "status": status,
        "valid": valid,
        "summary": {
            "blocks": block_count,
            "processed_blocks": rendered_result["processed_count"],
            "valid_json_blocks": sum(block.get("valid_json") is True for block in rendered_result["blocks"]),
            "invalid_json_blocks": sum(block.get("valid_json") is False for block in rendered_result["blocks"]),
            "entities": rendered_result["entity_count"],
            "types": rendered_result["types"],
            "errors": errors,
            "warnings": warnings,
            "info": infos,
        },
        "raw": raw_result,
        "rendered": rendered_result,
        "render_comparison": {
            "javascript_injected": javascript_injected,
            "raw_types": sorted(raw_types),
            "rendered_types": sorted(rendered_types),
            "rendered_only_types": rendered_only_types,
        },
        "findings": ordered_findings,
        "limitations": (["Validation was bounded because extraction limits were reached."] if truncated else []),
        "production_mutations": [],
        "paid_calls": [],
    }
    return render_payload, schema_payload


def _load_live(url: str, mode: str, timeout_ms: int) -> dict[str, Any]:
    dwight_home = Path(__file__).resolve().parents[3]
    source_root = Path(os.environ.get("CLAUDE_SEO_SOURCE_ROOT", dwight_home / "local" / "claude-seo"))
    scripts_dir = source_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from render_page import render_page  # type: ignore

    return render_page(url, mode=mode, timeout_ms=timeout_ms, extract_content=False)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dwight post-render Schema.org validation hook")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="Public URL to render and validate through the hardened renderer")
    source.add_argument("--html", help="Rendered/local HTML fixture to validate without network")
    parser.add_argument("--raw-html", help="Optional initial HTML fixture for JS-injection comparison")
    parser.add_argument("--target-url", help="Evidence target URL when --html is used")
    parser.add_argument("--mode", choices=("always", "auto", "never"), default="always")
    parser.add_argument("--timeout-ms", type=int, default=15_000)
    parser.add_argument("--evidence-dir", required=True, help="Directory receiving render.json and schema-validation.json")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when schema errors are found; artifacts are still written")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    evidence_dir = Path(args.evidence_dir).expanduser().resolve(strict=False)
    allowed_evidence_root = os.environ.get("DWIGHT_SCHEMA_EVIDENCE_ROOT")
    if allowed_evidence_root:
        allowed_root = Path(allowed_evidence_root).expanduser().resolve(strict=False)
        try:
            evidence_dir.relative_to(allowed_root)
        except ValueError:
            print(
                f"schema hook runtime error: evidence directory is outside allowed root {allowed_root}",
                file=sys.stderr,
            )
            return 2
    target_url = args.url or args.target_url
    if not target_url:
        print("--target-url is required with --html", file=sys.stderr)
        return 2

    try:
        if args.url:
            render = _load_live(args.url, args.mode, args.timeout_ms)
            raw_html = str(render.get("raw_content") or "")
            rendered_html = str(render.get("content") or raw_html)
            final_url = str(render.get("url") or args.url)
            mode_used = str(render.get("mode_used") or "unknown")
            status_code = render.get("status_code")
            is_spa = render.get("is_spa")
            render_engine = render.get("render_engine")
            diagnostics = list(render.get("render_diagnostics") or [])
            render_error = render.get("error")
        else:
            rendered_path = Path(args.html).expanduser()
            raw_path = Path(args.raw_html).expanduser() if args.raw_html else rendered_path
            rendered_html = rendered_path.read_text(encoding="utf-8", errors="replace")
            raw_html = raw_path.read_text(encoding="utf-8", errors="replace")
            final_url = target_url
            mode_used = "fixture"
            status_code = None
            is_spa = None
            render_engine = None
            diagnostics = []
            render_error = None

        render_payload, schema_payload = build_artifacts(
            target_url=target_url,
            raw_html=raw_html,
            rendered_html=rendered_html,
            final_url=final_url,
            mode_requested=args.mode,
            mode_used=mode_used,
            status_code=status_code,
            is_spa=is_spa,
            render_engine=render_engine,
            diagnostics=diagnostics,
            render_error=render_error,
        )
        _atomic_json_write(evidence_dir / "render.json", render_payload)
        _atomic_json_write(evidence_dir / "schema-validation.json", schema_payload)
    except Exception as exc:
        print(f"schema hook runtime error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "status": schema_payload["status"],
                "valid": schema_payload["valid"],
                "summary": schema_payload["summary"],
                "render_artifact": str(evidence_dir / "render.json"),
                "schema_artifact": str(evidence_dir / "schema-validation.json"),
            },
            ensure_ascii=False,
        )
    )
    if args.strict and schema_payload["status"] == "invalid":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
