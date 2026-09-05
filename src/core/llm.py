from functools import cache
from typing import Any

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from core.settings import settings
from schema.models import (
    AllModelEnum,
    AnthropicModelName,
    AWSModelName,
    AzureOpenAIModelName,
    DeepseekModelName,
    FakeModelName,
    GoogleModelName,
    GroqModelName,
    OllamaModelName,
    OpenAICompatibleName,
    OpenAIModelName,
    OpenRouterModelName,
    VertexAIModelName,
)

_MODEL_TABLE = (
    {m: m.value for m in OpenAIModelName}
    | {m: m.value for m in OpenAICompatibleName}
    | {m: m.value for m in AzureOpenAIModelName}
    | {m: m.value for m in DeepseekModelName}
    | {m: m.value for m in AnthropicModelName}
    | {m: m.value for m in GoogleModelName}
    | {m: m.value for m in VertexAIModelName}
    | {m: m.value for m in GroqModelName}
    | {m: m.value for m in AWSModelName}
    | {m: m.value for m in OllamaModelName}
    | {m: m.value for m in OpenRouterModelName}
    | {m: m.value for m in FakeModelName}
)


class FakeToolModel(FakeListChatModel):
    def __init__(self, responses: list[str] | None = None):
        if responses is None:
            responses = ["Autonomous revenue recovery processed successfully."]
        super().__init__(responses=responses)

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        return self


type ModelT = Any


@cache
def get_model(model_name: AllModelEnum, /) -> ModelT:
    api_model_name = _MODEL_TABLE.get(model_name)
    if not api_model_name:
        raise ValueError(f"Unsupported model: {model_name}")

    if model_name in OpenAIModelName:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=api_model_name, streaming=True)

    if model_name in OpenAICompatibleName:
        from langchain_openai import ChatOpenAI
        if not settings.COMPATIBLE_BASE_URL or not settings.COMPATIBLE_MODEL:
            raise ValueError("OpenAICompatible base url and endpoint must be configured")
        return ChatOpenAI(
            model=settings.COMPATIBLE_MODEL,
            temperature=0.5,
            streaming=True,
            openai_api_base=settings.COMPATIBLE_BASE_URL,
            openai_api_key=settings.COMPATIBLE_API_KEY,
        )

    if model_name in AzureOpenAIModelName:
        from langchain_openai import AzureChatOpenAI
        if not settings.AZURE_OPENAI_API_KEY or not settings.AZURE_OPENAI_ENDPOINT:
            raise ValueError("Azure OpenAI API key and endpoint must be configured")
        return AzureChatOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            deployment_name=api_model_name,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            streaming=True,
            timeout=60,
            max_retries=3,
        )

    if model_name in DeepseekModelName:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=api_model_name,
            temperature=0.5,
            streaming=True,
            openai_api_base="https://api.deepseek.com",
            openai_api_key=settings.DEEPSEEK_API_KEY,
        )

    if model_name in AnthropicModelName:
        from langchain_anthropic import ChatAnthropic
        if model_name == AnthropicModelName.SONNET_5:
            return ChatAnthropic(model_name=api_model_name, streaming=True)
        return ChatAnthropic(model_name=api_model_name, temperature=0.5, streaming=True)

    if model_name in GoogleModelName:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=api_model_name, temperature=0.5, streaming=True)

    if model_name in VertexAIModelName:
        from langchain_google_vertexai import ChatVertexAI
        return ChatVertexAI(model=api_model_name, temperature=0.5, streaming=True)

    if model_name in GroqModelName:
        from langchain_groq import ChatGroq
        return ChatGroq(model=api_model_name, temperature=0.5)

    if model_name in AWSModelName:
        from langchain_aws import ChatBedrock
        if model_name == AWSModelName.BEDROCK_SONNET:
            return ChatBedrock(model=api_model_name)
        return ChatBedrock(model=api_model_name, temperature=0.5)

    if model_name in OllamaModelName:
        from langchain_ollama import ChatOllama
        if not settings.OLLAMA_MODEL:
            raise ValueError("Ollama model must be configured")
        if settings.OLLAMA_BASE_URL:
            return ChatOllama(
                model=settings.OLLAMA_MODEL, temperature=0.5, base_url=settings.OLLAMA_BASE_URL
            )
        return ChatOllama(model=settings.OLLAMA_MODEL, temperature=0.5)

    if model_name in OpenRouterModelName:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=api_model_name,
            temperature=0.5,
            streaming=True,
            base_url="https://openrouter.ai/api/v1/",
            api_key=settings.OPENROUTER_API_KEY,
        )

    if model_name in FakeModelName:
        return FakeToolModel(responses=["Autonomous revenue recovery processed successfully."])

    raise ValueError(f"Unsupported model: {model_name}")
