#!/usr/bin/env python3
import json
import unittest

from local_schema_bundle import bundle, pointer


class BundleTest(unittest.TestCase):
    def run_bundle(self, ref, files=None, siblings=None):
        files = files or {}
        reads = []
        def read(path):
            reads.append(path)
            return files[path].encode()
        result = bundle({"components": {"schemas": {"Test": {"$ref": ref, **(siblings or {})}}}},
                        "api/openapi.yaml", read)
        return result["components"]["schemas"]["Test"], reads

    def test_nested_local_pointers_escaped_tokens_and_array_index(self):
        files = {"contracts/tool.json": json.dumps({"$defs": {
            "a/b~c": {"type": "string"}}, "items": [{"$ref": "#/$defs/a~1b~0c"}]})}
        result, reads = self.run_bundle("../contracts/tool.json#/items/0", files)
        self.assertEqual(result, {"type": "string"})
        self.assertEqual(reads, ["contracts/tool.json"])
        self.assertEqual(pointer({"a b": True}, "/a%20b"), True)

    def test_ref_siblings_remain_conjunctive(self):
        result, _ = self.run_bundle("../contracts/t.json", {"contracts/t.json": '{"type":"string"}'},
                                    {"type": "integer"})
        self.assertEqual(result, {"allOf": [{"type": "string"}, {"type": "integer"}]})

    def test_root_local_refs_and_literal_annotations_preserved(self):
        root = {"components": {"schemas": {"A": {"type": "object", "properties": {
            "child": {"$ref": "#/components/schemas/A"}}, "example": {"$ref": "https://literal"}}}}}
        self.assertEqual(bundle(root, "api/openapi.yaml", lambda path: self.fail(path)), root)

    def test_unsafe_paths_and_remote_refs_rejected_without_read(self):
        for ref in ("https://example/schema.json", "file:///tmp/a.json", "//host/a.json",
                    "/tmp/a.json", "../../a.json", "../%2e%2e/a.json", "..\\a.json",
                    "../contracts/a.json?x=y", "../contracts//a.json", "../contracts/a.yaml"):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                self.run_bundle(ref)

    def test_cycles_anchors_dynamic_refs_and_rebased_ids_rejected(self):
        values = [('{"$ref":"#"}', "cyclic"),
                  ('{"$anchor":"a","type":"string"}', "anchored"),
                  ('{"$dynamicRef":"#a"}', "dynamic"),
                  ('{"$id":"https://example/a.json","$ref":"b.json"}', "ambiguous"),
                  ('{"properties":{"x":{"$id":"nested"}}}', "nested")]
        for content, diagnostic in values:
            with self.subTest(content=content), self.assertRaisesRegex(ValueError, diagnostic):
                self.run_bundle("../contracts/t.json", {"contracts/t.json": content})

    def test_malformed_pointers_duplicates_and_non_schema_targets(self):
        for fragment in ("anchor", "/missing", "/items/01", "/~2", "/%QQ"):
            with self.subTest(fragment=fragment), self.assertRaises(ValueError):
                self.run_bundle("../contracts/t.json#" + fragment,
                                {"contracts/t.json": '{"items":[true]}'})
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.run_bundle("../contracts/t.json", {"contracts/t.json": '{"type":"string","type":"number"}'})
        with self.assertRaisesRegex(ValueError, "select a schema"):
            self.run_bundle("../contracts/t.json#/type", {"contracts/t.json": '{"type":"string"}'})

    def test_reused_references_are_deterministic_and_recursive_objects_fail_closed(self):
        files = {"contracts/t.json": '{"$defs":{"T":{"type":"string"}}}'}
        root = {"allOf": [
            {"$ref": "../contracts/t.json#/$defs/T"},
            {"$ref": "../contracts/t.json#/$defs/T"},
        ]}
        reads = []
        self.assertEqual(bundle(root, "api/openapi.yaml", lambda path: reads.append(path) or files[path].encode()),
                         {"allOf": [{"type": "string"}, {"type": "string"}]})
        self.assertEqual(reads, ["contracts/t.json"])
        cyclic = {}
        cyclic["properties"] = {"self": cyclic}
        with self.assertRaisesRegex(ValueError, "in-memory"):
            bundle(cyclic, "api/openapi.yaml", lambda path: self.fail(path))


if __name__ == "__main__":
    unittest.main()
