FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/SwordfishTrumpet/homewizard-cli"
LABEL org.opencontainers.image.description="Command-line tool for the HomeWizard P1 Meter"

RUN pip install --no-cache-dir homewizard-cli

ENTRYPOINT ["homewizard-cli"]
CMD ["--help"]
