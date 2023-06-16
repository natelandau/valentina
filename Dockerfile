

# Use an official Python runtime as a parent image
FROM python:3.11

# Set labels
LABEL org.opencontainers.image.source=https://github.com/natelandau/valentina
LABEL org.opencontainers.image.description="Valentina Noir, Discord bot."
LABEL org.opencontainers.image.licenses=MIT
LABEL org.opencontainers.image.url=https://github.com/natelandau/valentina
LABEL org.opencontainers.image.title="Valentina Noir"

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install git
RUN apt-get update && apt-get install -y git sqlite3

# Install Poetry
RUN pip install poetry

# Install valentina
RUN poetry install --without dev,test

# Run valentina when the container launches
CMD ["poetry", "run", "valentina"]
