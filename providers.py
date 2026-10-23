from dataclasses import dataclass
from openai import OpenAI

@dataclass
class ProviderConfig:
    name: str = "Google Gemini"
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    model: str = "gemini-2.5-flash"
    api_key: str = ""

PRESETS = {
    "Google Gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-2.5-flash"),
    "OpenRouter": ("https://openrouter.ai/api/v1", "openrouter/auto"),
    "Custom OpenAI-compatible": ("http://localhost:1234/v1", "local-model"),
}

def make_client(config: ProviderConfig) -> OpenAI:
    if not config.api_key.strip():
        raise ValueError("ابتدا کلید API را در تنظیمات وارد کنید.")
    if not config.base_url.strip() or not config.model.strip():
        raise ValueError("آدرس API و نام مدل الزامی است.")
    return OpenAI(api_key=config.api_key.strip(), base_url=config.base_url.strip())
