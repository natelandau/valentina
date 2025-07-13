FROM ghcr.io/astral-sh/uv:0.7.19-python3.13-bookworm-slim

# Set labels
LABEL org.opencontainers.image.source=https://github.com/natelandau/valentina
LABEL org.opencontainers.image.description="Valentina Noir, Discord bot."
LABEL org.opencontainers.image.licenses=MIT
LABEL org.opencontainers.image.url=https://github.com/natelandau/valentina
LABEL org.opencontainers.image.title="Valentina Noir"

# Install Apt Packages
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates tar git tzdata cron

# Set timezone
ENV TZ=Etc/UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ >/etc/timezone

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy the project into the image
ADD . /app

# Install dependencies
RUN uv sync --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint
ENTRYPOINT []

# Run valentina by default
CMD ["uv", "run", "valentina"]
