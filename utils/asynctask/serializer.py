import logging
from typing import (
    Type,
)
from .models import ModelClass

logger = logging.getLogger(__name__)


class Serializer:
    def unpack(self, data: bytes, model_class: Type[ModelClass] | None = None) -> ModelClass | None:
        raise NotImplemented()

    def pack(self, data: ModelClass | None = None) -> bytes:
        raise NotImplemented()

    def content_type(self) -> str:
        raise NotImplemented()


class JsonSerializer(Serializer):
    def unpack(self, data: bytes, model_class: Type[ModelClass] | None = None) -> ModelClass | None:
        if not model_class and not data:
            return None
        if not model_class and data:
            raise RuntimeError(f'Unexpected rpc result {data}')
        # if data == b'':
        #     return None
        # if not model_class:
        #     return None
        # if data is None:
        #     return None
        return model_class.model_validate_json(data)

    def pack(self, data: ModelClass | None = None) -> bytes:
        if data is None:
            return b''
        return data.model_dump_json().encode()

    def content_type(self) -> str:
        return 'application/json'
