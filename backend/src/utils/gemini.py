import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai._common import (
    get_client_info,
)
from typing_extensions import Self
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    model_validator,
)
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    cast,
)
from . import _genai_extension as genaix

logger = logging.getLogger(__name__)


class CustomChatGoogleGenerativeAI(ChatGoogleGenerativeAI):
    base_url: Optional[str] = None

    def __init__(self, *args, base_url: Optional[str] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = base_url

    @model_validator(mode="after")
    def validate_environment(self) -> Self:
        """Validates params and passes them to google-generativeai package."""
        if self.temperature is not None and not 0 <= self.temperature <= 1:
            raise ValueError("temperature must be in the range [0.0, 1.0]")

        if self.top_p is not None and not 0 <= self.top_p <= 1:
            raise ValueError("top_p must be in the range [0.0, 1.0]")

        if self.top_k is not None and self.top_k <= 0:
            raise ValueError("top_k must be positive")

        if not self.model.startswith("models/"):
            self.model = f"models/{self.model}"

        additional_headers = self.additional_headers or {}
        self.default_metadata = tuple(additional_headers.items())
        client_info = get_client_info("ChatGoogleGenerativeAI")
        google_api_key = None
        if not self.credentials:
            if isinstance(self.google_api_key, SecretStr):
                google_api_key = self.google_api_key.get_secret_value()
            else:
                google_api_key = self.google_api_key
        transport: Optional[str] = self.transport

        logger.debug("From validate_environment, base_url: %s", self.base_url)

        self.client = genaix.build_generative_service(
            credentials=self.credentials,
            api_key=google_api_key,
            client_info=client_info,
            client_options=self.client_options,
            transport=transport,
            base_url=self.base_url,
        )
        self.async_client_running = None
        return self
