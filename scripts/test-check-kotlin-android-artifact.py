#!/usr/bin/env python3
import importlib.util
import pathlib
import struct
import tempfile
import unittest
import zipfile

CHECKER = pathlib.Path(__file__).with_name("check-kotlin-android-artifact.py")
spec = importlib.util.spec_from_file_location("checker", CHECKER)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

def class_file(constants=b""):
    return b"\xca\xfe\xba\xbe" + struct.pack(">HHH", 0, 52, 1) + constants

def aar(path, classes, duplicate=False):
    jar = pathlib.Path(str(path) + ".jar")
    with zipfile.ZipFile(jar, "w") as output:
        for name, data in classes.items(): output.writestr(name, data)
        if duplicate: output.writestr(next(iter(classes)), class_file())
    with zipfile.ZipFile(path, "w") as output: output.write(jar, "classes.jar")

class ArtifactCheckTest(unittest.TestCase):
    def test_poisoned_constant_pools_fail_closed(self):
        header = b"\xca\xfe\xba\xbe" + struct.pack(">HH", 0, 52)
        for count, payload in [
            (0, b""),
            (2, b"\xff"),
            (2, b"\x01\x00\x10short"),
            (2, b"\x05" + b"\0" * 8),
            (3, b"\x06" + b"\0" * 7),
        ]:
            with self.subTest(count=count, payload=payload):
                with self.assertRaises(ValueError):
                    checker.parse_utf8_constants(header + struct.pack(">H", count) + payload)

    def test_expanded_jar_and_aggregate_class_bounds(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "sdk.aar"
            aar(path, self.complete())
            for setting in ("MAX_CLASSES_JAR", "MAX_CLASS", "MAX_TOTAL_CLASS_BYTES"):
                original = getattr(checker, setting)
                try:
                    setattr(checker, setting, 1)
                    with self.subTest(setting=setting), self.assertRaises(ValueError):
                        checker.inspect(path)
                finally:
                    setattr(checker, setting, original)

    def complete(self, extra=None):
        names = checker.REQUIRED | set(extra or [])
        return {name: class_file() for name in names}
    def test_valid_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "sdk.aar"; aar(path, self.complete()); checker.inspect(path)
    def test_forbidden_reference(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "sdk.aar"; aar(path, self.complete({"dev/tempera/sdk/JdkHttpTransport.class"}))
            with self.assertRaises(ValueError): checker.inspect(path)
    def test_missing_required(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "sdk.aar"; data = self.complete(); data.pop(next(iter(checker.REQUIRED))); aar(path, data)
            with self.assertRaises(ValueError): checker.inspect(path)
    def test_truncated_and_duplicate(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "sdk.aar"; data = self.complete(); data[next(iter(data))] = b"\xca\xfe"; aar(path, data)
            with self.assertRaises(ValueError): checker.inspect(path)
            aar(path, self.complete(), duplicate=True)
            with self.assertRaises(ValueError): checker.inspect(path)
    def test_long_double_slots_and_utf8_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "sdk.aar"; data = self.complete()
            data[next(iter(data))] = b"\xca\xfe\xba\xbe" + struct.pack(">HHH", 0, 52, 3) + b"\x05" + b"\0" * 8
            aar(path, data); checker.inspect(path)
            marker = b"java/net/http/HttpClient"; cp = b"\x01" + struct.pack(">H", len(marker)) + marker
            data[next(iter(data))] = b"\xca\xfe\xba\xbe" + struct.pack(">HHH", 0, 52, 2) + cp
            aar(path, data)
            with self.assertRaises(ValueError): checker.inspect(path)
    def test_size_limits_and_embedded_jars(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "sdk.aar"; aar(path, self.complete())
            old = checker.MAX_AAR; checker.MAX_AAR = 1
            try:
                with self.assertRaises(ValueError): checker.inspect(path)
            finally: checker.MAX_AAR = old
            aar(path, self.complete())
            with zipfile.ZipFile(path, "a") as output: output.writestr("libs/hidden.jar", b"jar")
            with self.assertRaises(ValueError): checker.inspect(path)

if __name__ == "__main__": unittest.main()
