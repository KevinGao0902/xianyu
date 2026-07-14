import re
from typing import Any, Dict, Optional


QUARK_LINK_RE = re.compile(r"https?://pan\.quark\.cn/s/[A-Za-z0-9_-]+", re.IGNORECASE)


def provision_material_fulfillment(
    db: Any,
    user_id: int,
    material: Dict[str, Any],
    *,
    item_title: Optional[str] = None,
    item_id: Optional[str] = None,
    keyword: Optional[str] = None,
    delay_seconds: int = 0,
) -> Dict[str, Any]:
    material_id = int(material["id"])
    marker = f"x-material:{material_id}"
    delivery_text = _build_delivery_text(material)
    match_keyword = str(keyword or item_title or material.get("title") or "").strip()
    if not match_keyword:
        raise ValueError("商品标题或发货匹配关键词不能为空")

    description = f"X资源自动发货；{marker}"
    if item_id:
        description += f"；item:{str(item_id).strip()}"

    card = next((row for row in db.get_all_cards(user_id) if marker in str(row.get("description") or "")), None)
    card_name = f"X资源发货-{material_id}-{str(material.get('title') or '资料')[:18]}"
    card_created = card is None
    if card_created:
        card_id = db.create_card(
            name=card_name,
            card_type="text",
            text_content=delivery_text,
            description=description,
            enabled=True,
            delay_seconds=max(0, int(delay_seconds or 0)),
            user_id=user_id,
        )
    else:
        card_id = int(card["id"])
        db.update_card(
            card_id,
            name=card_name,
            text_content=delivery_text,
            description=description,
            enabled=True,
            delay_seconds=max(0, int(delay_seconds or 0)),
            user_id=user_id,
        )

    rule = next((row for row in db.get_all_delivery_rules(user_id) if marker in str(row.get("description") or "")), None)
    rule_created = rule is None
    if rule_created:
        rule_id = db.create_delivery_rule(
            keyword=match_keyword,
            card_id=card_id,
            delivery_count=1,
            enabled=True,
            description=description,
            user_id=user_id,
        )
    else:
        rule_id = int(rule["id"])
        db.update_delivery_rule(
            rule_id,
            keyword=match_keyword,
            card_id=card_id,
            delivery_count=1,
            enabled=True,
            description=description,
            user_id=user_id,
        )

    return {
        "material_id": material_id,
        "card_id": card_id,
        "rule_id": rule_id,
        "keyword": match_keyword,
        "card_created": card_created,
        "rule_created": rule_created,
        "delivery_text": delivery_text,
    }


def _build_delivery_text(material: Dict[str, Any]) -> str:
    source = "\n".join([str(material.get("description") or ""), str(material.get("remark") or "")])
    links = list(dict.fromkeys(QUARK_LINK_RE.findall(source)))
    if not links:
        raise ValueError("商品素材中没有可用于发货的夸克网盘链接")
    title = str(material.get("title") or "数字资源").strip()
    return "\n".join([
        f"您好，您购买的《{title}》已整理完成：",
        *links,
        "请及时保存到自己的网盘；如链接异常，请在订单会话中联系处理。",
    ])
