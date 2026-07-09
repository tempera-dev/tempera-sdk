import unittest

from tempera_sdk import PRODUCTS, SCOPES, TemperaClient, TemperaSdkError


class TemperaSdkTest(unittest.TestCase):
    def test_product_surface(self):
        self.assertEqual(PRODUCTS["temp_js"].repository, "https://github.com/tempera-dev/temp.js")
        self.assertEqual(PRODUCTS["tempo"].repository, "https://github.com/tempera-dev/tempo")
        self.assertEqual(PRODUCTS["temp_os"].repository, "https://github.com/tempera-dev/tempOS")
        self.assertEqual(PRODUCTS["remi"].repository, "https://github.com/tempera-dev/remi")
        self.assertEqual(PRODUCTS["cradle"].repository, "https://github.com/tempera-dev/cradle")
        self.assertEqual(PRODUCTS["arrha"].repository, "https://github.com/tempera-dev/arrha")
        self.assertIn("mcp:invoke", SCOPES)
        self.assertIn("admin", SCOPES)

    def test_missing_endpoint_is_clear(self):
        client = TemperaClient()
        with self.assertRaises(TemperaSdkError):
            client.endpoint_for("remi")


if __name__ == "__main__":
    unittest.main()
