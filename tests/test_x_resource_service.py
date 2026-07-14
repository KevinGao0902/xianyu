import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock

import httpx

from x_resource_service import build_product_material, XResourceService, XResourceServiceError
from utils.item_publisher import ItemPublisher


class XResourceServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_resources_passes_filters_and_token(self):
        async def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.headers.get("Authorization"), "Bearer secret")
            self.assertEqual(request.url.params["stage"], "ready_for_material")
            self.assertEqual(request.url.params["q"], "AI")
            return httpx.Response(200, json={"items": [{"uniqueKey": "tweet:1"}], "total": 1})

        service = XResourceService(
            "http://x-resource.test",
            "secret",
            transport=httpx.MockTransport(handler),
        )
        result = await service.list_resources(stage="ready_for_material", query="AI")
        self.assertEqual(result["items"][0]["uniqueKey"], "tweet:1")

    async def test_detail_key_is_url_encoded(self):
        async def handler(request: httpx.Request) -> httpx.Response:
            self.assertTrue(request.url.raw_path.endswith(b"tweet%3A123"))
            return httpx.Response(200, json={"uniqueKey": "tweet:123"})

        service = XResourceService("http://x-resource.test", transport=httpx.MockTransport(handler))
        result = await service.get_resource("tweet:123")
        self.assertEqual(result["uniqueKey"], "tweet:123")

    async def test_upstream_error_has_readable_message(self):
        transport = httpx.MockTransport(lambda request: httpx.Response(401, json={"error": "bad token"}))
        service = XResourceService("http://x-resource.test", transport=transport)
        with self.assertRaisesRegex(XResourceServiceError, "bad token"):
            await service.health()

    async def test_process_resources_posts_keys_and_uses_long_timeout(self):
        async def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.method, "POST")
            self.assertEqual(request.url.path, "/api/integration/resources/process")
            self.assertEqual(json.loads(request.content), {"uniqueKeys": ["tweet:1", "tweet:2"]})
            return httpx.Response(200, json={"processedCount": 2})

        service = XResourceService("http://x-resource.test", transport=httpx.MockTransport(handler))
        result = await service.process_resources(["tweet:1", "tweet:2"])
        self.assertEqual(result["processedCount"], 2)

    def test_product_material_uses_original_assets_and_idempotency_marker(self):
        with TemporaryDirectory() as directory:
            image_path = Path(directory) / "source.jpg"
            image_path.write_bytes(b"original-image")
            material = build_product_material({
                "uniqueKey": "tweet:9",
                "title": "AI 资料合集",
                "description": "完整帖子描述",
                "category": "学习资料",
                "imagePaths": [str(image_path)],
                "imageUrls": ["https://img.example/second.jpg"],
                "ownQuarkShareUrl": "https://pan.quark.cn/s/own",
                "sourceUrl": "https://x.com/user/status/9",
            })
        self.assertEqual(material["remark"], "x-resource:tweet:9")
        self.assertEqual(material["images"][0]["filename"], "source.jpg")
        self.assertIn("content", material["images"][0])
        self.assertEqual(material["images"][1]["url"], "https://img.example/second.jpg")
        self.assertIn("https://pan.quark.cn/s/own", material["description"])
        self.assertEqual(material["price"], 0.99)
        self.assertEqual(material["original_price"], 99.0)
        self.assertEqual(material["delivery_method"], "无需邮寄")

    def test_publish_form_accepts_loaded_material_images(self):
        html = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text(encoding="utf-8")
        image_input = html.split('id="publishImages"', 1)[1].split('>', 1)[0]

        self.assertIn('value="无需邮寄" selected', html)
        self.assertIn('id="publishCurrentPrice" min="0" step="0.01" value="0.99"', html)
        self.assertIn('id="publishOriginalPrice" min="0" step="0.01" value="99"', html)
        self.assertNotIn("required", image_input)

    async def test_material_content_image_is_ready_for_upload(self):
        publisher = ItemPublisher("cookie2=value", "test-account")
        publisher.upload_image = AsyncMock(return_value={
            "url": "https://img.example/item.jpg",
            "width": 10,
            "height": 10,
        })

        result = await publisher.prepare_image_for_publish({
            "filename": "cover.jpg",
            "content": "aW1hZ2U=",
        })

        self.assertEqual(result["url"], "https://img.example/item.jpg")
        publisher.upload_image.assert_awaited_once_with(image_bytes=b"image", filename="cover.jpg")


if __name__ == "__main__":
    unittest.main()
