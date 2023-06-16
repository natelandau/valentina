

# Use an official Python runtime as a parent image
FROM python:3.11

# Set labels
LABEL org.opencontainers.image.source=https://github.com/natelandau/valentina
LABEL org.opencontainers.image.description="Valentina Noir, Discord bot."
LABEL org.opencontainers.image.licenses=MIT
LABEL org.opencontainers.image.url=https://github.com/natelandau/valentina
LABEL org.opencontainers.image.title="Valentina Noir"


LABEL org.opencontainers.image.authors="Alexis Saettler <alexis@saettler.org>" \
    org.opencontainers.image.title="MonicaHQ, the Personal Relationship Manager" \
    org.opencontainers.image.description="This is MonicaHQ, your personal memory! MonicaHQ is like a CRM but for the friends, family, and acquaintances around you." \
    org.opencontainers.image.url="https://monicahq.com" \
    org.opencontainers.image.vendor="Monica"

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install git
RUN apt-get update && apt-get install -y git sqlite3

# Install Poetry
RUN pip install poetry

# Add our entrypoint script
# COPY entrypoint.sh /entrypoint.sh
# RUN chmod +x /entrypoint.sh

# Set the entrypoint to our script
# ENTRYPOINT ["/entrypoint.sh"]

# Run valentina when the container launches
CMD ["poetry", "run", "valentina"]
