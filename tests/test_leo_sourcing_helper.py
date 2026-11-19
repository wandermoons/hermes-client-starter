from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "distributions"
    / "leo"
    / "skills"
    / "leo-flexible-sourcing"
    / "scripts"
    / "prepare_candidates.py"
)
FIXTURES = ROOT / "tests" / "fixtures" / "leo"


def run_helper(payload: dict, *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=cwd or ROOT,
        check=False,
    )


def valid_payload() -> dict:
    return {
        "sector": "independent retailers",
        "zone": "Example County",
        "target_count": 3,
        "target_notion_database": "database-placeholder",
        "candidates": [],
        "existing_records": [],
    }


class LeoSourcingHelperTests(unittest.TestCase):
    def test_fixture_output_is_exact_and_deterministic(self) -> None:
        payload = json.loads((FIXTURES / "helper_input.json").read_text(encoding="utf-8"))
        expected = json.loads((FIXTURES / "helper_expected.json").read_text(encoding="utf-8"))
        first = run_helper(payload)
        second = run_helper(payload)
        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(expected, json.loads(first.stdout))

    def test_missing_or_invalid_required_inputs_are_rejected(self) -> None:
        cases: list[dict] = []
        for key in ("sector", "zone", "target_count", "target_notion_database"):
            payload = valid_payload()
            payload.pop(key)
            cases.append(payload)
        for bad_count in (0, -1, True, "3"):
            payload = valid_payload()
            payload["target_count"] = bad_count
            cases.append(payload)
        for key in ("sector", "zone", "target_notion_database"):
            payload = valid_payload()
            payload[key] = "  "
            cases.append(payload)
        payload = valid_payload()
        payload["candidates"] = {}
        cases.append(payload)
        payload = valid_payload()
        payload["existing_records"] = "not-a-list"
        cases.append(payload)

        for payload in cases:
            with self.subTest(payload=payload):
                result = run_helper(payload)
                self.assertEqual(2, result.returncode)
                report = json.loads(result.stdout)
                self.assertEqual("validation_error", report["error"])
                self.assertTrue(report["details"])

    def test_duplicate_url_variants_are_collapsed_by_domain(self) -> None:
        payload = valid_payload()
        payload["candidates"] = [
            {"company_name": "One", "website": "https://www.Example.COM/a"},
            {"company_name": "One duplicate", "website": "http://example.com:80/b?x=1"},
        ]
        result = run_helper(payload)
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(["example.com"], [row["domain"] for row in report["selected"]])
        self.assertEqual("duplicate_candidate_domain", report["excluded"][0]["reason"])

    def test_existing_rows_are_deduplicated_by_domain_then_identity(self) -> None:
        payload = valid_payload()
        payload["candidates"] = [
            {
                "company_name": "Existing Domain",
                "website": "https://www.existing.example/new",
            },
            {
                "company_name": "Same Company LLC",
                "website": "https://new-domain.example",
                "phone": "+1 (555) 900-1000",
            },
            {
                "company_name": "Same Company LLC",
                "website": "https://another-domain.example",
                "email": "TEAM" + "@" + "SAME.EXAMPLE",
            },
            {"company_name": "Fresh", "website": "https://fresh.example"},
        ]
        payload["existing_records"] = [
            {"company_name": "Old name", "website": "http://existing.example"},
            {"company_name": "Same Company, LLC", "phone": "+1 555 900 1000"},
            {"company_name": "Same Company LLC", "email": "team" + "@" + "same.example"},
        ]
        result = run_helper(payload)
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(["fresh.example"], [row["domain"] for row in report["selected"]])
        self.assertEqual(
            [
                "duplicate_existing_domain",
                "duplicate_existing_identity",
                "duplicate_existing_identity",
            ],
            [row["reason"] for row in report["excluded"]],
        )

    def test_existing_domain_property_is_used_without_a_website(self) -> None:
        payload = valid_payload()
        payload["candidates"] = [
            {"company_name": "Acme", "website": "https://www.acme.example/contact"}
        ]
        payload["existing_records"] = [
            {"company_name": "Acme", "domain": "ACME.EXAMPLE"}
        ]
        result = run_helper(payload)
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual([], report["selected"])
        self.assertEqual("duplicate_existing_domain", report["excluded"][0]["reason"])

    def test_ip_literals_and_non_public_hostnames_are_rejected(self) -> None:
        payload = valid_payload()
        payload["candidates"] = [
            {"company_name": "IPv6", "website": "https://[2001:db8::1]/contact"},
            {"company_name": "Local", "website": "http://localhost:8080"},
            {"company_name": "Underscore", "website": "https://bad_host.example"},
        ]
        result = run_helper(payload)
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual([], report["selected"])
        self.assertEqual(
            ["invalid_website", "invalid_website", "invalid_website"],
            [row["reason"] for row in report["excluded"]],
        )

    def test_missing_site_records_are_excluded_and_target_count_caps_output(self) -> None:
        payload = valid_payload()
        payload["target_count"] = 2
        payload["candidates"] = [
            {"company_name": "No Site"},
            {"company_name": "One", "website": "one.example"},
            {"company_name": "Two", "website": "two.example"},
            {"company_name": "Three", "website": "three.example"},
        ]
        result = run_helper(payload)
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(["one.example", "two.example"], [row["domain"] for row in report["selected"]])
        self.assertEqual(1, report["counts"]["capped"])
        self.assertIn("missing_website", [row["reason"] for row in report["excluded"]])

    def test_helper_has_no_network_or_external_write_capability(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
        self.assertTrue(
            imported_roots.isdisjoint(
                {"httpx", "requests", "socket", "subprocess", "urllib3", "ftplib"}
            ),
            imported_roots,
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotEqual("open", node.func.id)
            if isinstance(node, ast.Attribute):
                self.assertNotIn(
                    node.attr,
                    {"write_text", "write_bytes", "unlink", "rename", "replace", "mkdir"},
                )

        payload = valid_payload()
        payload["candidates"] = [{"company_name": "One", "website": "one.example"}]
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory)
            before = sorted(path.relative_to(cwd) for path in cwd.rglob("*"))
            result = run_helper(payload, cwd=cwd)
            after = sorted(path.relative_to(cwd) for path in cwd.rglob("*"))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
