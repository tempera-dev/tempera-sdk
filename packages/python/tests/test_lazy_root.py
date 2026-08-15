import json
import subprocess
import sys
import unittest


class LazyRootImportTest(unittest.TestCase):
    def run_isolated(self, source: str) -> dict[str, object]:
        completed = subprocess.run(
            [sys.executable, "-c", source],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(completed.stdout)

    def test_provider_root_import_does_not_load_unrelated_client_stacks(self):
        observed = self.run_isolated(
            """
import json, sys
from tempera_sdk import TemperaProvider
app = TemperaProvider('isolated')
print(json.dumps({
    'name': app.name,
    'auth': 'tempera_sdk.auth' in sys.modules,
    'client': 'tempera_sdk.client' in sys.modules,
    'mcp': 'tempera_sdk.mcp' in sys.modules,
    'surface': 'tempera_sdk.surface' in sys.modules,
    'provider': 'tempera_sdk.provider' in sys.modules,
    'provider_capabilities': 'tempera_sdk.provider_capabilities' in sys.modules,
}))
"""
        )
        self.assertEqual(observed["name"], "isolated")
        self.assertFalse(observed["auth"])
        self.assertFalse(observed["client"])
        self.assertFalse(observed["mcp"])
        self.assertFalse(observed["surface"])
        self.assertTrue(observed["provider"])
        self.assertTrue(observed["provider_capabilities"])

    def test_deprecated_api_targets_alias_preserves_identity(self):
        observed = self.run_isolated(
            """
import json, sys
import tempera_sdk
same = tempera_sdk.API_TARGETS is tempera_sdk.ENVIRONMENTS
print(json.dumps({
    'same': same,
    'surface': 'tempera_sdk.surface' in sys.modules,
    'auth': 'tempera_sdk.auth' in sys.modules,
    'client': 'tempera_sdk.client' in sys.modules,
}))
"""
        )
        self.assertTrue(observed["same"])
        self.assertTrue(observed["surface"])
        self.assertFalse(observed["auth"])
        self.assertFalse(observed["client"])

    def test_all_declared_root_exports_resolve(self):
        observed = self.run_isolated(
            """
import json
import tempera_sdk
missing = []
for name in tempera_sdk.__all__:
    try:
        getattr(tempera_sdk, name)
    except Exception as error:
        missing.append([name, type(error).__name__])
print(json.dumps({'missing': missing, 'dirContainsAll': set(tempera_sdk.__all__) <= set(dir(tempera_sdk))}))
"""
        )
        self.assertEqual(observed["missing"], [])
        self.assertTrue(observed["dirContainsAll"])


if __name__ == "__main__":
    unittest.main()
