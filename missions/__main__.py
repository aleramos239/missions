import uvicorn

from . import config

uvicorn.run("missions.api:app", host="127.0.0.1", port=config.PORT, log_level="warning")
