#!/usr/bin/env bash

# clone the repo
git clone https://github.com/natelandau/valentina.git /app

# Get new tags from remote
git fetch --tags

# Get latest tag name
latestTag=$(git describe --tags "$(git rev-list --tags --max-count=1)")

# Checkout latest tag
if git checkout -b "branch-$latestTag" "$latestTag"; then
    echo "Using: $latestTag"
else
    echo "Failed to checkout latest tag: $latestTag"
    exit 1
fi

# Install dependencies using Poetry
poetry install --without dev,test

# Run the command passed in docker-compose
exec "$@"
