import base64
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

import httpx


class XResourceServiceError(RuntimeError):
    pass


class XResourceService:
    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("X_RESOURCE_SERVICE_URL") or "http://127.0.0.1:5178").rstrip("/")
        self.token = token if token is not None else os.getenv("X_RESOURCE_API_TOKEN", "")
        self.transport = transport

    async def health(self) -> Dict[str, Any]:
        return await self._get("/api/integration/health")

    async def list_resources(
        self,
        page: int = 1,
        page_size: int = 20,
        stage: str = "",
        query: str = "",
    ) -> Dict[str, Any]:
        return await self._get(
            "/api/integration/resources",
            params={"page": page, "pageSize": page_size, "stage": stage, "q": query},
        )

    async def get_resource(self, unique_key: str) -> Dict[str, Any]:
        return await self._get(f"/api/integration/resources/{quote(unique_key, safe='')}")

    async def process_resources(self, unique_keys: list[str]) -> Dict[str, Any]:
        return await self._request(
            "POST",
            "/api/integration/resources/process",
            json={"uniqueKeys": unique_keys},
            timeout=600.0,
        )

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        timeout: float = 15.0,
    ) -> Dict[str, Any]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=timeout,
                transport=self.transport,
            ) as client:
                response = await client.request(method, path, params=params, json=json)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            detail = _response_error(exc.response)
            raise XResourceServiceError(f"X resource service returned {exc.response.status_code}: {detail}") from exc
        except (httpx.RequestError, ValueError) as exc:
            raise XResourceServiceError(f"X resource service is unavailable: {exc}") from exc


def _response_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
        return str(payload.get("error") or payload.get("detail") or payload)
    except ValueError:
        return response.text[:300] or "unknown error"


x_resource_service = XResourceService()


def build_product_material(resource: Dict[str, Any], default_price: float = 0.99) -> Dict[str, Any]:
    unique_key = str(resource.get("uniqueKey") or "").strip()
    title = str(resource.get("title") or "未命名资源").strip()[:30]
    description_parts = [str(resource.get("description") or title).strip()]
    own_share_url = str(resource.get("ownQuarkShareUrl") or "").strip()
    extract_code = str(resource.get("ownQuarkExtractCode") or "").strip()
    if own_share_url:
        description_parts.append(f"夸克网盘：{own_share_url}{f' 提取码：{extract_code}' if extract_code else ''}")
    source_url = str(resource.get("sourceUrl") or "").strip()
    if source_url:
        description_parts.append(f"内容来源：{source_url}")

    images = []
    seen = set()
    for raw_path in resource.get("imagePaths") or []:
        file_path = Path(str(raw_path))
        if not file_path.is_file():
            continue
        resolved = str(file_path.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        images.append({"filename": file_path.name, "content": base64.b64encode(file_path.read_bytes()).decode("ascii")})
        if len(images) >= 9:
            break
    for raw_url in resource.get("imageUrls") or []:
        url = str(raw_url or "").strip()
        if len(images) >= 9:
            break
        if not url.startswith(("http://", "https://")) or url in seen:
            continue
        seen.add(url)
        images.append({"url": url})

    return {
        "title": title,
        "description": "\n\n".join(part for part in description_parts if part),
        "price": float(default_price),
        "original_price": 99.0,
        "category": resource.get("category") or None,
        "images": images,
        "delivery_method": "无需邮寄",
        "postage": 0,
        "can_self_pickup": False,
        "condition": "全新",
        "remark": f"x-resource:{unique_key}",
    }
