"""AiGateway：DeepSeek（OpenAI 兼容）统一网关（开发规划 5.3 / PRD 8.6）。

职责：超时（连接 10s / 生成可配）、重试（429 指数退避）、JSON 修复、
缓存（相同题干+配置）、mock 降级、成本日志。
"""
import asyncio
import hashlib
import json
import logging
import re
import time

import httpx

from app.core.config import get_settings
from app.core.crypto import decrypt, encrypt
from app.core.errors import ApiError
from app.db.models import Setting

logger = logging.getLogger("recall")

_CACHE: dict[str, str] = {}


def _cache_key(messages: list[dict]) -> str:
    payload = json.dumps(messages, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


class AiGateway:
    """业务层统一入口。mock=True 时全部走本地模拟，不发起网络请求。"""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()

    # ---- API Key 存取（加密落盘）----
    @staticmethod
    def get_api_key(db) -> str:
        row = db.get(Setting, "ai_secret")
        if row is None or row.value_json == "null":
            return ""
        try:
            return decrypt(json.loads(row.value_json)["api_key"])
        except Exception:  # 密钥文件更换等异常：视为未配置
            return ""

    @staticmethod
    def set_api_key(db, api_key: str) -> None:
        row = db.get(Setting, "ai_secret")
        value = json.dumps({"api_key": encrypt(api_key)})
        if row is None:
            db.add(Setting(key="ai_secret", value_json=value))
        else:
            row.value_json = value

    # ---- 基础调用 ----
    async def _chat_once(self, messages: list[dict], *, json_mode: bool = False, stream: bool = False,
                         base_url: str | None = None, model: str | None = None, api_key: str | None = None):
        settings = self.settings
        url = (base_url or settings.deepseek_base_url).rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key if api_key is not None else settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model or settings.deepseek_model,
            "messages": messages,
            "stream": stream,
            "temperature": 0.2,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        timeout = httpx.Timeout(
            connect=settings.deepseek_timeout_connect,
            read=settings.deepseek_timeout_generate,
            write=30,
            pool=10,
        )
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.post(url, json=body, headers=headers)

    async def _chat_with_retry(self, messages: list[dict], *, json_mode: bool = False, max_retries: int = 3):
        """429/5xx 指数退避重试；仍失败抛 AI_UNAVAILABLE（EX-06）。"""
        delay = 1.0
        last_err: Exception | None = None
        for attempt in range(max_retries):
            try:
                resp = await self._chat_once(messages, json_mode=json_mode)
                if resp.status_code == 429 or resp.status_code >= 500:
                    last_err = ApiError("AI_UNAVAILABLE", "AI 服务暂时繁忙，请稍后重试", {})
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                resp.raise_for_status()
                return resp.json()
            except ApiError:
                raise
            except (httpx.TimeoutException, httpx.TransportError) as err:
                last_err = err
                await asyncio.sleep(delay)
                delay *= 2
        logger.warning("ai_gateway_retry_exhausted", extra={"error": str(last_err)})
        raise ApiError("AI_UNAVAILABLE", "AI 服务暂时繁忙，请稍后重试", {})

    @staticmethod
    def repair_json(text: str) -> dict | list:
        """JSON 修复（PRD 8.6）：提取代码块/首个 { }，补全括号。"""
        text = text.strip()
        block = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
        if block:
            text = block.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # 截取第一个 { 或 [ 到最后一个 } 或 ]
        start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=-1)
        if start < 0:
            raise ApiError("AI_UNAVAILABLE", "AI 返回内容无法解析，请重试", {})
        end = max(text.rfind("}"), text.rfind("]"))
        candidate = text[start:end + 1]
        # 补全右括号
        open_brackets = candidate.count("{") - candidate.count("}")
        open_squares = candidate.count("[") - candidate.count("]")
        candidate += "}" * max(open_brackets, 0) + "]" * max(open_squares, 0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as err:
            raise ApiError("AI_UNAVAILABLE", "AI 返回内容无法解析，请重试", {}) from err

    # ---- 对外接口 ----
    async def complete(self, messages: list[dict], *, use_cache: bool = True) -> str:
        """非流式补全（拆题/归档/变体/批改共用）。"""
        key = _cache_key(messages)
        if use_cache and key in _CACHE:
            return _CACHE[key]
        if self.settings.ai_mock:
            return self._mock_complete(messages)
        data = await self._chat_with_retry(messages)
        content = data["choices"][0]["message"]["content"]
        if use_cache and len(_CACHE) > 512:
            _CACHE.pop(next(iter(_CACHE)))
        if use_cache:
            _CACHE[key] = content
        return content

    async def complete_json(self, messages: list[dict], *, use_cache: bool = True) -> dict | list:
        text = await self.complete(messages, use_cache=use_cache)
        return self.repair_json(text)

    async def stream(self, messages: list[dict]):
        """SSE 流式：逐 chunk yield delta 文本。"""
        if self.settings.ai_mock:
            mock_text = self._mock_complete(messages)
            for i in range(0, len(mock_text), 8):
                await asyncio.sleep(0.01)
                yield mock_text[i:i + 8]
            return
        data = await self._chat_with_retry(messages)
        content = data["choices"][0]["message"]["content"]
        for i in range(0, len(content), 8):
            yield content[i:i + 8]

    async def ping(self, *, base_url: str | None = None, model: str | None = None,
                   api_key: str | None = None) -> dict:
        """测试连接（设置页）。mock 模式直接返回。"""
        if self.settings.ai_mock and api_key is None:
            return {"ok": True, "latency_ms": 1, "model": model or self.settings.deepseek_model,
                    "mock": True, "message": "当前为演示模式（mock），无需 API Key"}
        started = time.monotonic()
        try:
            resp = await self._chat_once(
                [{"role": "user", "content": "ping"}],
                base_url=base_url, model=model, api_key=api_key,
            )
            latency = int((time.monotonic() - started) * 1000)
            if resp.status_code == 401:
                return {"ok": False, "latency_ms": latency, "model": model or "", "mock": False,
                        "message": "API Key 无效（401）"}
            resp.raise_for_status()
            return {"ok": True, "latency_ms": latency, "model": model or self.settings.deepseek_model,
                    "mock": False, "message": "连接成功"}
        except (httpx.TimeoutException, httpx.TransportError) as err:
            latency = int((time.monotonic() - started) * 1000)
            return {"ok": False, "latency_ms": latency, "model": model or "", "mock": False,
                    "message": f"连接失败：{err.__class__.__name__}"}

    @staticmethod
    def _mock_complete(messages: list[dict]) -> str:
        """mock 模式：返回可解析的模拟内容（保证主流程可演示，R1/R2 缓解）。"""
        last = messages[-1]["content"] if messages else ""
        return (
            "（演示模式 mock 响应）这是 AI 根据题干生成的解析内容。"
            f"你提出的问题是：{last[:40]}。"
            "请配置 DeepSeek API Key 后获得真实 AI 输出（设置 → AI API 配置）。"
        )


_gateway: AiGateway | None = None


def get_gateway() -> AiGateway:
    global _gateway
    if _gateway is None:
        _gateway = AiGateway()
    return _gateway
