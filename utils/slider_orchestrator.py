"""滑块验证编排与严格结果判定工具。

本模块先提供轻量级编排/判定能力：调用现有 XianyuSliderStealth 后，
必须拿到 x5/x5sec 相关 Cookie 才认为平台真正放行，避免“视觉通过但
未下发 x5sec”被误当成功而导致 token 刷新死循环。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple


DEFAULT_SLIDER_ENGINE = "playwright"


@dataclass(frozen=True)
class SliderVerificationResult:
    """标准化滑块验证结果。"""

    success: bool
    cookies: Optional[Dict[str, Any]]
    engine: str
    x5_cookies: Dict[str, Any]
    message: str

    def as_legacy_tuple(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """兼容旧调用方的 ``(success, cookies)`` 返回格式。"""
        return self.success, self.cookies


def extract_x5_cookies(cookies: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """提取 x5/x5sec 相关 Cookie。"""
    if not isinstance(cookies, Mapping):
        return {}

    result: Dict[str, Any] = {}
    for name, value in cookies.items():
        name_lower = str(name or "").lower()
        if name_lower.startswith("x5") or "x5sec" in name_lower:
            result[str(name)] = value
    return result


def has_x5_cookie(cookies: Optional[Mapping[str, Any]]) -> bool:
    """判断浏览器返回 Cookie 中是否包含真正放行用的 x5/x5sec 票据。"""
    return bool(extract_x5_cookies(cookies))


def validate_slider_result(
    success: bool,
    cookies: Optional[Mapping[str, Any]],
    *,
    engine: Optional[str] = DEFAULT_SLIDER_ENGINE,
) -> SliderVerificationResult:
    """严格判定滑块结果。

    旧逻辑只要页面视觉上通过且返回了任意 Cookie 就可能进入成功分支。
    闲鱼/阿里风控下，视觉通过但没有下发 x5sec 时，后续 token 接口仍会
    继续返回验证要求。因此这里强制要求 x5/x5sec 相关 Cookie。
    """
    normalized_engine = str(engine or DEFAULT_SLIDER_ENGINE).strip() or DEFAULT_SLIDER_ENGINE
    normalized_cookies = dict(cookies or {}) if isinstance(cookies, Mapping) else None
    x5_cookies = extract_x5_cookies(normalized_cookies)

    if not success:
        return SliderVerificationResult(
            success=False,
            cookies=None,
            engine=normalized_engine,
            x5_cookies={},
            message="滑块验证失败",
        )

    if not normalized_cookies:
        return SliderVerificationResult(
            success=False,
            cookies=None,
            engine=normalized_engine,
            x5_cookies={},
            message="滑块视觉通过但未返回 Cookie，平台可能未真正放行",
        )

    if not x5_cookies:
        return SliderVerificationResult(
            success=False,
            cookies=normalized_cookies,
            engine=normalized_engine,
            x5_cookies={},
            message=(
                "滑块视觉通过但未获取到 x5sec Cookie，判定为失败；"
                "常见原因是浏览器环境/IP 仍被风控拦截"
            ),
        )

    return SliderVerificationResult(
        success=True,
        cookies=normalized_cookies,
        engine=normalized_engine,
        x5_cookies=x5_cookies,
        message="滑块验证成功并获取到 x5sec Cookie",
    )


def run_slider_strict(slider: Any, url: str, *, engine: Optional[str] = DEFAULT_SLIDER_ENGINE, **kwargs: Any) -> SliderVerificationResult:
    """调用同步 slider.run，并进行严格 x5sec 判定。"""
    success, cookies = slider.run(url, **kwargs)
    return validate_slider_result(success, cookies, engine=engine)


async def run_slider_async_strict(
    slider: Any,
    url: str,
    *,
    engine: Optional[str] = DEFAULT_SLIDER_ENGINE,
    **kwargs: Any,
) -> SliderVerificationResult:
    """调用异步 slider.async_run，并进行严格 x5sec 判定。"""
    success, cookies = await slider.async_run(url, **kwargs)
    return validate_slider_result(success, cookies, engine=engine)
