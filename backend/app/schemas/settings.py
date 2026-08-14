"""设置 DTO：学科、AI API 配置、隐私、默认复习配置、令牌掩码。"""
from pydantic import BaseModel, Field


class AiConfig(BaseModel):
    provider: str = "deepseek"
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    api_key_masked: str = ""  # 前端只显示掩码
    has_api_key: bool = False
    mock: bool = True


class PrivacyConfig(BaseModel):
    send_question_to_ai: bool = True  # 允许关闭 AI 数据流向
    lan_enabled: bool = False


class DefaultReviewConfig(BaseModel):
    count: int = 5
    difficulty: str = "auto"
    scope: str = "due"


class SettingsOut(BaseModel):
    ai: AiConfig
    privacy: PrivacyConfig
    default_review: DefaultReviewConfig
    token_masked: str
    version: str


class SettingsUpdate(BaseModel):
    ai: AiConfig | None = None  # 允许改 base_url/model/api_key（api_key 明文写入时前端传 "set"）
    api_key: str | None = None
    privacy: PrivacyConfig | None = None
    default_review: DefaultReviewConfig | None = None


class TestAiRequest(BaseModel):
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None


class TestAiResponse(BaseModel):
    ok: bool
    latency_ms: int
    model: str
    mock: bool
    message: str = ""
