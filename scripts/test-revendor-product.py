#!/usr/bin/env python3
"""Credential custody regressions for authenticated producer re-vendoring."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "revendor_product", Path(__file__).with_name("revendor-product.py")
)
revendor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(revendor)


class CredentialCustody(unittest.TestCase):
    def test_clone_keeps_credentials_out_of_arguments_and_logs(self):
        token = "fixture-token-never-a-real-credential"
        output = io.StringIO()
        with patch.dict(os.environ, {"GH_TOKEN": token}, clear=True), \
                patch.object(revendor.subprocess, "run") as execute, \
                contextlib.redirect_stdout(output):
            revendor.clone("tempera-dev/fixture", "main", "a" * 40, Path("checkout"))
        self.assertNotIn(token, output.getvalue())
        self.assertNotIn(revendor._basic(token), output.getvalue())
        for call in execute.call_args_list:
            command = call.args[0]
            self.assertNotIn(token, repr(command))
            self.assertNotIn(revendor._basic(token), repr(command))
            self.assertNotEqual(command[1], "config")
            self.assertEqual(call.kwargs["env"]["GIT_CONFIG_VALUE_0"],
                             "Authorization: Basic " + revendor._basic(token))
        self.assertEqual(execute.call_args_list[0].args[0][-2],
                         "https://github.com/tempera-dev/fixture.git")

    def test_failed_clone_does_not_disclose_credentials(self):
        token = "fixture-failure-token"
        def fail(command, **kwargs):
            raise subprocess.CalledProcessError(1, command)
        with patch.dict(os.environ, {"GITHUB_TOKEN": token}, clear=True), \
                patch.object(revendor.subprocess, "run", side_effect=fail), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(subprocess.CalledProcessError) as failure:
                revendor.clone("tempera-dev/fixture", "main", "a" * 40, Path("checkout"))
        self.assertNotIn(token, str(failure.exception))
        self.assertNotIn(revendor._basic(token), str(failure.exception))

    def test_existing_process_config_and_parent_environment_are_preserved(self):
        original = {"GITHUB_TOKEN": "fixture", "GIT_CONFIG_COUNT": "1",
                    "GIT_CONFIG_KEY_0": "core.hooksPath", "GIT_CONFIG_VALUE_0": "/dev/null"}
        with patch.dict(os.environ, original, clear=True):
            environment = revendor.git_environment()
            self.assertEqual(dict(os.environ), original)
        self.assertEqual(environment["GIT_CONFIG_COUNT"], "2")
        self.assertEqual(environment["GIT_CONFIG_VALUE_0"], "/dev/null")
        self.assertEqual(environment["GIT_CONFIG_KEY_1"], "http.https://github.com/.extraheader")

    def test_no_token_leaves_git_authentication_unchanged(self):
        with patch.dict(os.environ, {"PATH": "/usr/bin"}, clear=True):
            self.assertEqual(revendor.git_environment(), {"PATH": "/usr/bin"})


if __name__ == "__main__":
    unittest.main()
