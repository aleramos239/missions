import uvicorn

from . import config


def main():
    uvicorn.run("missions.api:app", host="127.0.0.1", port=config.PORT, log_level="warning",
                timeout_graceful_shutdown=5)


if __name__ == "__main__":
    main()
