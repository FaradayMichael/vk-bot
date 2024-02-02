import mimetypes
import re
import textwrap
import hashlib

from base64 import b64decode as decode64
from base64 import b64encode as encode64
from typing import Any

from urllib.parse import quote, unquote

from pydantic import GetJsonSchemaHandler, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

MIMETYPE_REGEX = r"[\w]+\/[\w\-\+\.]+"
_MIMETYPE_RE = re.compile("^{}$".format(MIMETYPE_REGEX))

CHARSET_REGEX = r"[\w\-\+\.]+"
_CHARSET_RE = re.compile("^{}$".format(CHARSET_REGEX))

DATA_URI_REGEX = (
        r"data:"
        + r"(?P<mimetype>{})?".format(MIMETYPE_REGEX)
        + r"(?:\;name\=(?P<name>[\w\.\-%!*'~\(\)]+))?"
        + r"(?:\;charset\=(?P<charset>{}))?".format(CHARSET_REGEX)
        + r"(?P<base64>\;base64)?"
        + r",(?P<data>.*)"
)
_DATA_URI_RE = re.compile(r"^{}$".format(DATA_URI_REGEX), re.DOTALL)


class InvalidMimeType(ValueError):
    pass


class InvalidCharset(ValueError):
    pass


class InvalidDataURL(ValueError):
    pass


class DataURL(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler):
        return core_schema.no_info_after_validator_function(cls, handler(str))

    # @classmethod
    # @typing_extensions.deprecated(
    #     'The `validate` method is deprecated; use `model_validate` instead.', category=PydanticDeprecatedSince20
    # )
    # def validate(cls: type[Model], value: Any) -> Model:  # noqa: D102
    #     #warnings.warn('The `validate` method is deprecated; use `model_validate` instead.', DeprecationWarning)
    #     return cls.model_validate(value)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler):
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema.update(
            pattern='data:[<тип данных>][;base64],<данные>',
        )
        return json_schema

    @classmethod
    def make(cls, mimetype, charset, base64, data):
        parts = ["data:"]
        if mimetype is not None:
            if not _MIMETYPE_RE.match(mimetype):
                raise InvalidMimeType("Invalid mimetype: %r" % mimetype)
            parts.append(mimetype)
        if charset is not None:
            if not _CHARSET_RE.match(charset):
                raise InvalidCharset("Invalid charset: %r" % charset)
            parts.extend([";charset=", charset])
        if base64:
            parts.append(";base64")
            _charset = charset or "utf-8"
            if isinstance(data, bytes):
                _data = data
            else:
                _data = bytes(data, _charset)
            encoded_data = encode64(_data).decode(_charset).strip()
        else:
            encoded_data = quote(data)
        parts.extend([",", encoded_data])
        return cls("".join(parts))

    @classmethod
    def from_file(cls, filename, charset=None, base64=True):
        mimetype, _ = mimetypes.guess_type(filename, strict=False)
        with open(filename, "rb") as fp:
            data = fp.read()

        return cls.make(mimetype, charset, base64, data)

    def __new__(cls, *args, **kwargs):
        uri = super(DataURL, cls).__new__(cls, *args, **kwargs)
        uri._parsed = uri._parse  # Trigger any ValueErrors on instantiation.
        uri._md5 = hashlib.md5(uri.data).hexdigest()
        return uri

    def __repr__(self):
        return "DataURL(%s)" % (super(DataURL, self).__repr__(),)

    def wrap(self, width=76):
        return "\n".join(textwrap.wrap(self, width, break_on_hyphens=False))

    @property
    def mimetype(self):
        return self._parsed[0]

    @property
    def name(self):
        name = self._parsed[1]
        if name is not None:
            return unquote(name)
        return name

    @property
    def charset(self):
        return self._parsed[2]

    @property
    def is_base64(self):
        return self._parsed[3]

    @property
    def data(self):
        return self._parsed[4]

    @property
    def text(self):
        if self.charset is None:
            raise InvalidCharset("DataURL has no encoding set.")

        return self.data.decode(self.charset)

    @property
    def md5(self):
        return self._md5

    @property
    def _parse(self):
        match = _DATA_URI_RE.match(self)
        if not match:
            raise InvalidDataURL("Not a valid data URI: %r" % self)
        mimetype = match.group("mimetype") or None
        name = match.group("name") or None
        charset = match.group("charset") or None

        if match.group("base64"):
            _charset = charset or "utf-8"
            _data = bytes(match.group("data"), _charset)
            data = decode64(_data)
        else:
            data = unquote(match.group("data"))

        return mimetype, name, charset, bool(match.group("base64")), data

    def ext(self) -> str:
        return self.get_ext(self.mimetype)

    @staticmethod
    def get_ext(mimetype: str) -> str:
        match mimetype:
            case "text/plain":
                return "txt"
            case "image/png":
                return "png"
            case "image/jpeg":
                return "jpeg"
            case "image/gif":
                return "gif"
            case "image/bmp":
                return "bmp"
            case "application/msword":
                return "doc"
            case "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                return "docx"
            case "application/vnd.oasis.opendocument.text":
                return "odt"
            case "application/vnd.oasis.opendocument.spreadsheet":
                return "ods"
            case "application/pdf":
                return "pdf"
            case "application/vnd.ms-excel":
                return "xls"
            case "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                return "xlsx"
            case _:
                raise RuntimeError(f'Тип {mimetype} не поддерживается')
