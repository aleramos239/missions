import uvicorn

from . import config


def main():
    uvicorn.run("missions.api:app", host="127.0.0.1", port=config.PORT, log_level="warning")


if __name__ == "__main__":
    main()
