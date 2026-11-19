#!/usr/bin/env python3
"""Deterministically normalize and deduplicate supplied candidates.

This helper reads one JSON object from standard input and emits one JSON
report to standard output. It performs no discovery, network I/O, or writes.
"""

from __future__ import annotations

import ipaddress
import json
import re
import sys
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urlsplit


IdentityKey = Tuple[str, str, str]
HOST_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")


def clean_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def normalize_company(value: Any) -> str:
    text = unicodedata.normalize("NFKD", clean_text(value).casefold())
    text = "".join(character for character in text if not unicodedata.combining(character))
    return "".join(character for character in text if character.isalnum())


def normalize_phone(value: Any) -> str:
    return "".join(character for character in clean_text(value) if character.isdigit())


def normalize_email(value: Any) -> str:
    return clean_text(value).casefold()


def canonicalize_website(value: Any) -> Tuple[Optional[str], Optional[str]]:
    raw = clean_text(value)
    if not raw:
        return None, None
    candidate = raw if "://" in raw else "https://" + raw
    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError:
        return None, None
    if parsed.scheme.casefold() not in {"http", "https"}:
        return None, None
    if parsed.username or parsed.password or not parsed.hostname:
        return None, None

    host = parsed.hostname.casefold().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        return None, None
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return None, None
    labels = host.split(".")
    if (
        len(host) > 253
        or len(labels) < 2
        or any(not HOST_LABEL.fullmatch(label) for label in labels)
    ):
        return None, None

    scheme = parsed.scheme.casefold()
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    port_suffix = "" if port is None or default_port else ":" + str(port)
    return f"{scheme}://{host}{port_suffix}", host


def identity_keys(record: Dict[str, Any]) -> Set[IdentityKey]:
    company = normalize_company(record.get("company_name"))
    if not company:
        return set()
    keys: Set[IdentityKey] = set()
    phone = normalize_phone(record.get("phone"))
    email = normalize_email(record.get("email"))
    if phone:
        keys.add(("company_phone", company, phone))
    if email:
        keys.add(("company_email", company, email))
    return keys


def normalized_record(record: Dict[str, Any], website: str, domain: str) -> Dict[str, Any]:
    output: Dict[str, Any] = {}
    for key, value in record.items():
        if key not in {"website", "domain", "email", "company_name"}:
            output[key] = value
    output = {
        "company_name": clean_text(record.get("company_name")),
        "website": website,
        "domain": domain,
        **output,
    }
    email = normalize_email(record.get("email"))
    if "phone" in record:
        output["phone"] = record["phone"]
    if email:
        output["email"] = email
    return output


def validation_errors(payload: Any) -> List[str]:
    if not isinstance(payload, dict):
        return ["input must be a JSON object"]
    errors: List[str] = []
    for key in ("sector", "zone", "target_notion_database"):
        if not clean_text(payload.get(key)):
            errors.append(f"{key} must be a non-empty string")
    target_count = payload.get("target_count")
    if isinstance(target_count, bool) or not isinstance(target_count, int) or target_count <= 0:
        errors.append("target_count must be a positive integer")
    if not isinstance(payload.get("candidates"), list):
        errors.append("candidates must be a list")
    if not isinstance(payload.get("existing_records"), list):
        errors.append("existing_records must be a list")
    return errors


def existing_indexes(records: Iterable[Any]) -> Tuple[Set[str], Set[IdentityKey]]:
    domains: Set[str] = set()
    identities: Set[IdentityKey] = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        for value in (record.get("website"), record.get("domain")):
            _, domain = canonicalize_website(value)
            if domain:
                domains.add(domain)
        identities.update(identity_keys(record))
    return domains, identities


def prepare(payload: Dict[str, Any]) -> Dict[str, Any]:
    existing_records = payload["existing_records"]
    existing_domains, existing_identities = existing_indexes(existing_records)
    candidate_domains: Set[str] = set()
    candidate_identities: Set[IdentityKey] = set()
    eligible: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []

    for index, candidate in enumerate(payload["candidates"]):
        company_name = clean_text(candidate.get("company_name")) if isinstance(candidate, dict) else ""
        exclusion: Dict[str, Any] = {"index": index, "company_name": company_name}
        if not isinstance(candidate, dict):
            exclusion["reason"] = "invalid_candidate"
            excluded.append(exclusion)
            continue
        if not company_name:
            exclusion["reason"] = "missing_company_name"
            excluded.append(exclusion)
            continue

        raw_website = clean_text(candidate.get("website"))
        if not raw_website:
            exclusion["reason"] = "missing_website"
            excluded.append(exclusion)
            continue
        website, domain = canonicalize_website(raw_website)
        if not website or not domain:
            exclusion["reason"] = "invalid_website"
            excluded.append(exclusion)
            continue
        exclusion["domain"] = domain

        keys = identity_keys(candidate)
        if domain in existing_domains:
            exclusion["reason"] = "duplicate_existing_domain"
            excluded.append(exclusion)
            continue
        if keys & existing_identities:
            exclusion["reason"] = "duplicate_existing_identity"
            excluded.append(exclusion)
            continue
        if domain in candidate_domains:
            exclusion["reason"] = "duplicate_candidate_domain"
            excluded.append(exclusion)
            continue
        if keys & candidate_identities:
            exclusion["reason"] = "duplicate_candidate_identity"
            excluded.append(exclusion)
            continue

        eligible.append(normalized_record(candidate, website, domain))
        candidate_domains.add(domain)
        candidate_identities.update(keys)

    target_count = payload["target_count"]
    selected = eligible[:target_count]
    capped = max(0, len(eligible) - target_count)
    return {
        "mission": {
            "sector": clean_text(payload["sector"]),
            "zone": clean_text(payload["zone"]),
            "target_count": target_count,
            "target_notion_database": clean_text(payload["target_notion_database"]),
        },
        "selected": selected,
        "excluded": excluded,
        "counts": {
            "input_candidates": len(payload["candidates"]),
            "existing_records": len(existing_records),
            "eligible_unique": len(eligible),
            "selected": len(selected),
            "excluded": len(excluded),
            "capped": capped,
        },
    }


def emit(payload: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError) as error:
        emit({"error": "validation_error", "details": [f"invalid JSON: {error}"]})
        return 2

    errors = validation_errors(payload)
    if errors:
        emit({"error": "validation_error", "details": errors})
        return 2
    emit(prepare(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
