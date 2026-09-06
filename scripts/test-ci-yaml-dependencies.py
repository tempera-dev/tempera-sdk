#!/usr/bin/env python3
"""Keep YAML-dependent vendored-source tests runnable in both CI entry points."""
from pathlib import Path
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/test.yml"
INSTALL = "python3 -m pip install PyYAML==6.0.3"
TEST = "python3 scripts/test-sync-vendored-openapi.py"


class CiYamlDependencyTest(unittest.TestCase):
    def test_data_exact_source_job_installs_pinned_yaml_before_provenance_test(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        job = content.split("      - name: Verify exact committed Data Engine source", 1)[1].split(
            "\n\n  auth-hub-exact-source:", 1
        )[0]
        self.assertIn(INSTALL, job)
        self.assertIn(TEST, job)
        self.assertLess(job.index(INSTALL), job.index(TEST))

    def test_generic_sdk_job_installs_pinned_yaml_before_provenance_test(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        job = content.split("\n  sdk:\n", 1)[1]
        self.assertIn(INSTALL, job)
        self.assertIn(TEST, job)
        self.assertLess(job.index(INSTALL), job.index(TEST))


if __name__ == "__main__":
    unittest.main()
