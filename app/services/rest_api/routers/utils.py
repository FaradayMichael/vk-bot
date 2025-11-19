import base64
import logging

from fastapi import (
    APIRouter,
    File,
    UploadFile,
    Depends,
)
from fastapi.responses import (
    JSONResponse,
)

from app.schemas.utils import SpeechToTextResponse
from app.services.utils.client import UtilsClient
from app.utils.dataurl import DataURL
from app.utils.fastapi.depends.utils_clinet import get as get_utils_client
from app.utils.fastapi.handlers import error_400

logger = logging.getLogger(__name__)

_prefix = "/utils"
_tags = ["utils"]

router = APIRouter(prefix=_prefix, tags=_tags)
SUPPORTED_FORMATS = [
    ".wav",
]


@router.post(
    "/speech_to_text",
    response_model=SpeechToTextResponse,
    description=f"Supported formats: {', '.join(SUPPORTED_FORMATS)}",
)
async def api_speech_to_text(
    file: UploadFile = File(...),
    utils_client: UtilsClient = Depends(get_utils_client),
) -> SpeechToTextResponse | JSONResponse:
    if not any([f in file.filename for f in SUPPORTED_FORMATS]):
        return await error_400("Format not supported")

    response = await utils_client.speech_to_text(
        file.filename,
        DataURL.make(
            mimetype=file.content_type,
            charset=None,
            base64=True,
            data=base64.b64encode(file.file.read()).decode("ascii"),
        ),
    )
    return SpeechToTextResponse(text=response.text)
