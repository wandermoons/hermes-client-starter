from __future__ import annotations

import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SUFFIXES = {
    ".csv", ".ini", ".json", ".md", ".py", ".sh", ".toml",
    ".txt", ".xml", ".yaml", ".yml",
}
PRIVATE_DENYLIST = tuple(
    term.strip().lower()
    for term in os.environ.get("DWIGHT_PRIVATE_DENYLIST", "").split(",")
    if term.strip()
)
PLACEHOLDERS = {
    "", "...", "null", "none", "changeme", "example", "placeholder",
    "redacted", "your-value", "your_value",
}
PERSONAL_PATH_PATTERNS = (
    re.compile(r"/Users/[A-Za-z0-9._-]+"),
    re.compile(r"/home/[A-Za-z0-9._-]+"),
    re.compile(r"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+", re.IGNORECASE),
)
SENSITIVE_VALUE = re.compile(
    r"(?im)(?:^|[,{\s])[\"']?"
    r"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|"
    r"private[_-]?key|password|passwd|secret|token)"
    r"[\"']?\s*[:=]\s*[\"']?([^\s,}\"'#]+)"
)
AUTHENTICATED_URL = re.compile(r"https?://[^/\s:@]+:[^@\s/]+@", re.IGNORECASE)
BEARER_VALUE = re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{20,}")
EMAIL_VALUE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
TOKEN_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
)
PRIVATE_KEY_SENTINELS = ("-----BEGIN " + "PRIVATE KEY-----",) + tuple(
    "-----BEGIN " + kind + " PRIVATE KEY-----"
    for kind in ("OPENSSH", "RSA", "EC")
)


def public_files() -> list[Path]:
    paths: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if path.suffix.lower() in PUBLIC_SUFFIXES or path.name == "VERSION":
            paths.append(path)
    return paths


def normalized_secret_value(value: str) -> str:
    return value.strip().strip("'\"<>").lower()


def secret_violations(text: str, *, scan_generic_assignments: bool = True) -> list[str]:
    violations: list[str] = []
    if any(sentinel in text for sentinel in PRIVATE_KEY_SENTINELS):
        violations.append("private key")
    if AUTHENTICATED_URL.search(text):
        violations.append("authenticated URL")
    if BEARER_VALUE.search(text):
        violations.append("bearer token")
    if EMAIL_VALUE.search(text):
        violations.append("email address")
    for pattern in TOKEN_PATTERNS:
        if pattern.search(text):
            violations.append("provider token")
            break
    if scan_generic_assignments:
        for match in SENSITIVE_VALUE.finditer(text):
            raw_value = match.group(1).strip().strip("'\"")
            value = normalized_secret_value(match.group(1))
            if (
                value not in PLACEHOLDERS
                and not value.startswith("${")
                and not (raw_value.startswith("<") and raw_value.endswith(">"))
            ):
                violations.append("non-empty sensitive value")
    return violations


class DwightCoreSanitizationTests(unittest.TestCase):
    def test_no_private_denylist_terms(self) -> None:
        self.assertTrue(
            PRIVATE_DENYLIST,
            "Set DWIGHT_PRIVATE_DENYLIST for the mandatory private release scan",
        )
        violations: list[str] = []
        for path in public_files():
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            for term in PRIVATE_DENYLIST:
                if term in text:
                    violations.append(f"{path.relative_to(ROOT)}: private denylist term")
        self.assertEqual([], violations)

    def test_no_personal_absolute_paths(self) -> None:
        violations: list[str] = []
        for path in public_files():
            text = path.read_text(encoding="utf-8", errors="replace")
            for pattern in PERSONAL_PATH_PATTERNS:
                if pattern.search(text):
                    violations.append(f"{path.relative_to(ROOT)}: personal absolute path")
        self.assertEqual([], violations)

    def test_no_secret_values_keys_tokens_emails_or_authenticated_urls(self) -> None:
        violations: list[str] = []
        for path in public_files():
            text = path.read_text(encoding="utf-8", errors="replace")
            for violation in secret_violations(
                text,
                scan_generic_assignments=path.suffix.lower() not in {".py", ".sh"},
            ):
                violations.append(f"{path.relative_to(ROOT)}: {violation}")
        self.assertEqual([], violations)

    def test_secret_scanner_detects_common_synthetic_shapes(self) -> None:
        samples = (
            ("api" + "_key") + ": synthetic-sensitive-value-123",
            '{"access' + '_token":"synthetic-sensitive-value-456"}',
            "-----BEGIN " + "OPENSSH PRIVATE KEY-----\nsynthetic",
            "sk" + "-" + ("A" * 24),
            "https://" + "synthetic-user" + ":" + "synthetic-pass" + "@example.invalid/path",
            "Bearer " + ("A" * 24),
            "synthetic.user" + "@" + "example.invalid",
        )
        for sample in samples:
            self.assertTrue(secret_violations(sample), sample)

    def test_brand_voice_skill_requires_authorization_provenance_and_non_copying(self) -> None:
        path = ROOT / "distributions" / "dwight" / "skills" / "dwight-brand-voice-extraction" / "SKILL.md"
        text = path.read_text(encoding="utf-8").lower()
        for concept in (
            "sitemap", "échantillon", "url", "date", "autorisé",
            "descriptive", "n-gram", "plagi", "brand_voice_guide.md",
        ):
            self.assertIn(concept, text)
        self.assertNotIn("public or supplied with authorization", text)
        self.assertNotIn("vocabulary, recurring expressions", text)

    def test_wordpress_skill_has_no_draft_without_approval_contradiction(self) -> None:
        path = ROOT / "distributions" / "dwight" / "skills" / "dwight-wordpress-safe-operations" / "SKILL.md"
        text = path.read_text(encoding="utf-8").lower()
        for concept in (
            "toute mutation", "validation explicite", "status=draft", "https",
            "redirection", "etag", "sauvegarde", "api", "public",
        ):
            self.assertIn(concept, text)
        self.assertNotIn("new content defaults to `draft`", text)
        self.assertNotIn("use `draft` unless publication", text)
        self.assertIn("rendered public title/meta only for published content", text)
        self.assertIn("without any public probe", text)
        self.assertNotIn("verify the write response and rendered public title/meta.", text)

    def test_market_intelligence_has_no_paid_retry_contradiction(self) -> None:
        path = ROOT / "distributions" / "dwight" / "skills" / "dwight-seo-market-intelligence" / "SKILL.md"
        text = path.read_text(encoding="utf-8").lower()
        for concept in (
            "google search console", "dataforseo", "budget préautorisé",
            "coût maximal", "ne re-poste jamais", "identifiant de tâche",
        ):
            self.assertIn(concept, text)
        self.assertNotIn("retry a failed external call once", text)
        self.assertNotIn("before a significant dataforseo expense", text)
        self.assertNotIn("material dépense", text)

    def test_internal_linking_never_publicly_probes_private_drafts(self) -> None:
        path = ROOT / "distributions" / "dwight" / "skills" / "dwight-seo-internal-linking" / "SKILL.md"
        text = path.read_text(encoding="utf-8").lower()
        self.assertIn("never probe it publicly", text)
        self.assertIn("public rendering is checked only for published content", text)
        self.assertNotIn("\n4. fetch rendered public html.", text)

    def test_readme_has_strict_paid_call_policy(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        self.assertIn("budget préautorisé et plafonné", text)
        self.assertNotIn("dépenses importantes", text)

    def test_research_core_has_strict_paid_call_policy(self) -> None:
        path = ROOT / "distributions" / "dwight" / "skills" / "dwight-research-core" / "SKILL.md"
        text = path.read_text(encoding="utf-8").lower()
        self.assertIn("any paid research call", text)
        self.assertIn("preauthorized capped budget", text)
        self.assertNotIn("paid bulk research", text)

    def test_onboarding_has_strict_paid_call_policy(self) -> None:
        path = ROOT / "skills" / "client-agent-onboarding" / "SKILL.md"
        text = path.read_text(encoding="utf-8").lower()
        self.assertIn("toute requête payante", text)
        self.assertIn("tout appel sonar potentiellement facturé", text)
        self.assertGreaterEqual(text.count("budget préautorisé et plafonné"), 2)
        self.assertIn("coût maximal", text)
        self.assertNotIn("réaliser une requête peu coûteuse", text)
        self.assertNotIn("effectuer un vrai appel sonar", text)


if __name__ == "__main__":
    unittest.main()
