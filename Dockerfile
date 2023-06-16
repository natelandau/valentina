# Use an official Python runtime as a parent image
FROM python:3.11

# Set the working directory in the container to /app
WORKDIR /app

# Install git
RUN apt-get update && apt-get install -y git sqlite3

# Install Poetry
RUN pip install poetry

# Add our entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set the entrypoint to our script
ENTRYPOINT ["/entrypoint.sh"]

# Run valentina when the container launches
CMD ["poetry", "run", "valentina"]
