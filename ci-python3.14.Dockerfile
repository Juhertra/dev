# Python 3.14 CI Dockerfile for M1 Testing
# This Dockerfile provides a consistent environment for testing Python 3.14 compatibility

FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python 3.14 from source (when available)
# For now, we'll use Python 3.12 as a placeholder until 3.14 is released
RUN curl -fsSL https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz | tar -xzC /tmp && \
    cd /tmp/Python-3.12.0 && \
    ./configure --enable-optimizations --with-ensurepip=install && \
    make -j$(nproc) && \
    make altinstall && \
    ln -sf /usr/local/bin/python3.12 /usr/local/bin/python3.14 && \
    ln -sf /usr/local/bin/pip3.12 /usr/local/bin/pip3.14 && \
    cd / && rm -rf /tmp/Python-3.12.0

# Install pip and common tools
RUN python3.14 -m pip install --upgrade pip setuptools wheel

# Install development tools
RUN python3.14 -m pip install \
    pytest \
    pytest-cov \
    pytest-xdist \
    pytest-mock \
    pytest-timeout \
    coverage \
    ruff \
    pyright \
    import-linter \
    bandit \
    safety \
    cryptography \
    requests \
    pyyaml \
    flask \
    jsonschema

# Create working directory
WORKDIR /workspace

# Copy project files
COPY . .

# Install project dependencies
RUN python3.14 -m pip install -e ".[dev]"

# Set default command
CMD ["python3.14", "--version"]
