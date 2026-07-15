import re
from typing import Any, Dict, Optional


QUARK_LINK_RE = re.compile(r"https?://pan\.quark\.cn/s/[A-Za-z0-9_-]+", re.IGNORECASE)
EXTRACT_CODE_RE = re.compile(r"(?:提取码|访问码)\s*[:：]?\s*([A-Za-z0-9]{2,12})", re.IGNORECASE)


def _build_presale_reply(material: Dict[str, Any]) -> str:
    title = str(material.get("title") or "数字资料").strip()
    return (
        f"您好，《{title}》是数字资料商品。下单并付款后系统会自动发送夸克网盘链接；"
        "如需了解资料范围或遇到链接问题，可以直接留言。"
    )


def provision_material_fulfillment(
    db: Any,
    user_id: int,
    material: Dict[str, Any],
    *,
    item_title: Optional[str] = None,
    item_id: Optional[str] = None,
    account_id: Optional[str] = None,
    keyword: Optional[str] = None,
    delay_seconds: int = 0,
    presale_reply: Optional[str] = None,
) -> Dict[str, Any]:
    material_id = int(material["id"])
    marker = f"x-material:{material_id}"
    effective_material = dict(material)
    if str(item_title or "").strip():
        effective_material["title"] = str(item_title).strip()
    delivery_text = _build_delivery_text(effective_material)
    match_keyword = str(keyword or item_title or material.get("title") or "").strip()
    if not match_keyword:
        raise ValueError("商品标题或发货匹配关键词不能为空")

    card_description = f"X资源自动发货；{marker}"
    clean_item_id = str(item_id or "").strip()
    rule_marker = f"{marker};item:{clean_item_id}" if clean_item_id else marker
    rule_description = f"X资源自动发货；{rule_marker}"

    card = next((row for row in db.get_all_cards(user_id) if marker in str(row.get("description") or "")), None)
    card_name = f"X资源发货-{material_id}-{str(material.get('title') or '资料')[:18]}"
    card_created = card is None
    if card_created:
        card_id = db.create_card(
            name=card_name,
            card_type="text",
            text_content=delivery_text,
            description=card_description,
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
            description=card_description,
            enabled=True,
            delay_seconds=max(0, int(delay_seconds or 0)),
            user_id=user_id,
        )

    all_rules = db.get_all_delivery_rules(user_id)
    rule = next(
        (row for row in all_rules if str(row.get("description") or "").endswith(rule_marker)),
        None,
    )
    if rule is None and clean_item_id:
        rule = next(
            (row for row in all_rules if str(row.get("description") or "").endswith(marker)),
            None,
        )
    rule_created = rule is None
    if rule_created:
        rule_id = db.create_delivery_rule(
            keyword=match_keyword,
            card_id=card_id,
            delivery_count=1,
            enabled=True,
            description=rule_description,
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
            description=rule_description,
            user_id=user_id,
        )

    clean_account_id = str(account_id or "").strip()
    item_reply_configured = False
    item_reply = str(presale_reply or _build_presale_reply(effective_material)).strip()
    if clean_account_id and clean_item_id:
        item_reply_configured = bool(
            db.update_item_reply(clean_account_id, clean_item_id, item_reply)
        )
        if not item_reply_configured:
            raise ValueError("商品售前自动回复保存失败")

    return {
        "material_id": material_id,
        "card_id": card_id,
        "rule_id": rule_id,
        "keyword": match_keyword,
        "card_created": card_created,
        "rule_created": rule_created,
        "delivery_text": delivery_text,
        "item_reply": item_reply,
        "item_reply_configured": item_reply_configured,
    }


def _build_delivery_text(material: Dict[str, Any]) -> str:
    source = "\n".join([str(material.get("description") or ""), str(material.get("remark") or "")])
    delivery_lines = []
    seen_links = set()
    source_lines = source.splitlines()
    for index, line in enumerate(source_lines):
        for link in QUARK_LINK_RE.findall(line):
            normalized_link = link.rstrip(".,，。;；)")
            if normalized_link.lower() in seen_links:
                continue
            seen_links.add(normalized_link.lower())
            nearby_text = "\n".join(source_lines[index:index + 2])
            extract_code_match = EXTRACT_CODE_RE.search(nearby_text)
            delivery_line = normalized_link
            if extract_code_match:
                delivery_line += f"  提取码：{extract_code_match.group(1)}"
            delivery_lines.append(delivery_line)
    if not delivery_lines:
        raise ValueError("商品素材中没有可用于发货的夸克网盘链接")
    title = str(material.get("title") or "数字资源").strip()
    return "\n".join([
        f"您好，您购买的《{title}》已整理完成：",
        *delivery_lines,
        "请及时保存到自己的网盘；如链接异常，请在订单会话中联系处理。",
    ])
