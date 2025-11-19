import uvicorn

from app.utils import log
from app.services.rest_api.main import factory

slog = log
app = factory()

PORT = 8010
HOST = "0.0.0.0"

if __name__ == "__main__":
    uvicorn.run(app="rest_api:app", host=HOST, port=PORT, reload=True)
