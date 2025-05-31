# Use a Python image with uv pre-installed
FROM python:3.13-slim-bookworm

# Set labels
LABEL org.opencontainers.image.source=https://github.com/natelandau/valentina
LABEL org.opencontainers.image.description="Valentina Noir, Discord bot."
LABEL org.opencontainers.image.licenses=MIT
LABEL org.opencontainers.image.url=https://github.com/natelandau/valentina
LABEL org.opencontainers.image.title="Valentina Noir"

# Install Apt Packages
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates tar git tzdata

COPY --from=ghcr.io/astral-sh/uv:0.7.9 /uv /uvx /bin/

# Set timezone
ENV TZ=Etc/UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ >/etc/timezone

# Copy the project into the image
ADD . /app

# Sync the project into a new environment, asserting the lockfile is up to date
WORKDIR /app
RUN uv sync --locked

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Run valentina by default
CMD ["uv", "run", "valentina"]
