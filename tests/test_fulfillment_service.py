import unittest

from fulfillment_service import provision_material_fulfillment


class FakeDb:
    def __init__(self):
        self.cards = []
        self.rules = []
        self.item_replies = {}

    def get_all_cards(self, user_id):
        return self.cards

    def create_card(self, **values):
        self.cards.append({"id": 1, **values})
        return 1

    def update_card(self, card_id, **values):
        self.cards[0].update(values)
        return True

    def get_all_delivery_rules(self, user_id):
        return self.rules

    def create_delivery_rule(self, **values):
        self.rules.append({"id": 2, **values})
        return 2

    def update_delivery_rule(self, rule_id, **values):
        self.rules[0].update(values)
        return True

    def update_item_reply(self, cookie_id, item_id, reply_content):
        self.item_replies[(cookie_id, item_id)] = reply_content
        return True


class FulfillmentServiceTests(unittest.TestCase):
    def test_provision_is_idempotent_and_updates_keyword(self):
        db = FakeDb()
        material = {
            "id": 7,
            "title": "AI资料包",
            "description": "下载地址 https://pan.quark.cn/s/demo123",
            "remark": "x-resource:tweet:7",
        }
        first = provision_material_fulfillment(db, 3, material, item_title="闲鱼标题")
        second = provision_material_fulfillment(
            db,
            3,
            material,
            account_id="account-1",
            item_title="新标题",
            item_id="9988",
        )
        self.assertTrue(first["card_created"])
        self.assertFalse(second["card_created"])
        self.assertEqual(len(db.cards), 1)
        self.assertEqual(len(db.rules), 1)
        self.assertEqual(db.rules[0]["keyword"], "新标题")
        self.assertIn("item:9988", db.rules[-1]["description"])
        self.assertTrue(second["item_reply_configured"])
        self.assertNotIn("pan.quark.cn", db.item_replies[("account-1", "9988")])

    def test_delivery_text_keeps_extract_code(self):
        db = FakeDb()
        material = {
            "id": 9,
            "title": "资料包",
            "description": "夸克网盘：https://pan.quark.cn/s/demo999 提取码：A8K2",
        }

        result = provision_material_fulfillment(db, 3, material, item_title="资料包")

        self.assertIn("https://pan.quark.cn/s/demo999  提取码：A8K2", result["delivery_text"])

    def test_delivery_text_reads_extract_code_from_next_line(self):
        db = FakeDb()
        material = {
            "id": 10,
            "title": "资料包",
            "description": "夸克网盘：https://pan.quark.cn/s/demo-next\n提取码：B7M9",
        }

        result = provision_material_fulfillment(db, 3, material, item_title="发布标题")

        self.assertIn("《发布标题》", result["delivery_text"])
        self.assertIn("提取码：B7M9", result["delivery_text"])

    def test_rejects_material_without_quark_link(self):
        with self.assertRaisesRegex(ValueError, "没有可用于发货"):
            provision_material_fulfillment(FakeDb(), 3, {"id": 8, "title": "空素材"})


if __name__ == "__main__":
    unittest.main()
