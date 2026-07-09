import unittest

from tempera_sdk import API_TARGETS, PRODUCTS, SCOPES, TemperaClient, TemperaSdkError


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
        self.assertEqual(API_TARGETS["production"]["control_plane_url"], "https://api.tempera.dev")
        self.assertEqual(API_TARGETS["production"]["palette_mcp_url"], "https://mcp.tempera.dev/mcp")
        self.assertEqual(API_TARGETS["production"]["tempo_api_url"], "https://tempo.tempera.dev")

    def test_missing_endpoint_is_clear(self):
        client = TemperaClient()
        with self.assertRaises(TemperaSdkError):
            client.endpoint_for("remi")


if __name__ == "__main__":
    unittest.main()
