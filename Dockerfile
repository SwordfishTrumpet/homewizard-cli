FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/SwordfishTrumpet/homewizard-cli"
LABEL org.opencontainers.image.description="Command-line tool for the HomeWizard P1 Meter"

# Build from the checkout, not from the index: `pip install homewizard-cli`
# installed whatever release PyPI served at build time, so an image built from
# a commit or tag could silently contain different code (issue #31).
WORKDIR /app
COPY pyproject.toml README.md ./
COPY homewizard_cli ./homewizard_cli
RUN pip install --no-cache-dir .

ENTRYPOINT ["homewizard-cli"]
CMD ["--help"]
