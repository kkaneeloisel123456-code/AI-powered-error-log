"""OcrClient 抽象（开发规划 3.3：OCR 可替换实现或 mock）。

- MockOcrClient（默认，RECALL_OCR_MOCK=true）：返回内置多题样例文本，保证主流程可演示；
- PaddleOcrClient：对接 PaddleOCR-VL 本地推理服务（PaddleX pipeline HTTP 端点），
  默认图片不出本机（隐私默认，PRD 6.3）。
"""
import logging
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.errors import ApiError

logger = logging.getLogger("recall")

# mock 文本：一道物理 + 一道数学（拆题后应得到 2 张候选题卡）
MOCK_OCR_TEXT = """第1题：一物体从静止开始做匀加速直线运动，加速度为 2m/s²，求 5s 内的位移。
A. 10m
B. 25m
C. 50m
D. 100m
第2题：已知函数 f(x)=x³-3x，求 f(x) 的单调区间。"""


class OcrClient:
    """OCR 客户端接口。"""

    async def recognize(self, image_path: Path) -> str:
        raise NotImplementedError


class MockOcrClient(OcrClient):
    """演示模式：不读图，返回内置多题样例（R1 缓解：保证录入闭环可演示）。"""

    async def recognize(self, image_path: Path) -> str:
        return MOCK_OCR_TEXT


class PaddleOcrClient(OcrClient):
    """PaddleOCR-VL（PaddleX pipeline）本地推理。

    要求本机或局域网有 PaddleX 服务（默认 http://127.0.0.1:8010/ocr）。
    图片以 multipart 提交，不经过第三方服务器。
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8010/ocr"):
        self.base_url = base_url

    async def recognize(self, image_path: Path) -> str:
        timeout = httpx.Timeout(connect=10, read=30)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                with image_path.open("rb") as fh:
                    resp = await client.post(
                        self.base_url,
                        files={"file": (image_path.name, fh, "image/*")},
                    )
                resp.raise_for_status()
                data = resp.json()
                text = data.get("text") or data.get("result", {}).get("text", "")
                if not text.strip():
                    raise ApiError("OCR_FAILED", "未识别到清晰文字，请重拍或换图；可改用文本录入", {})
                return text
        except ApiError:
            raise
        except (httpx.TimeoutException, httpx.TransportError) as err:
            logger.warning("paddle_ocr_unreachable", extra={"error": str(err)})
            raise ApiError("OCR_FAILED", "未识别到清晰文字，请重拍或换图；可改用文本录入", {}) from err


def get_ocr_client() -> OcrClient:
    settings = get_settings()
    if settings.ocr_mock:
        return MockOcrClient()
    return PaddleOcrClient()
