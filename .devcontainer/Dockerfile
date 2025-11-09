# Development Environment Dockerfile for eBook2Audiobook
# Optimized for development with all necessary tools and best practices

FROM python:3.12-slim

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.7.1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build essentials
    gcc \
    g++ \
    make \
    cmake \
    build-essential \
    # Version control
    git \
    git-lfs \
    # Download tools
    wget \
    curl \
    # Audio/Video processing
    calibre \
    ffmpeg \
    sox \
    libsndfile1-dev \
    espeak-ng \
    # Japanese language support
    libmecab-dev \
    mecab \
    mecab-ipadic-utf8 \
    # Node.js (for some TTS engines)
    nodejs \
    npm \
    # Development tools
    vim \
    nano \
    less \
    htop \
    tree \
    jq \
    # Network tools
    net-tools \
    iputils-ping \
    # Debugging
    gdb \
    strace \
    # Shell
    zsh \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (required for phonemizer-fork)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Create non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python development tools
RUN pip install --upgrade pip setuptools wheel && \
    pip install \
    # Testing
    pytest \
    pytest-cov \
    pytest-xdist \
    pytest-mock \
    pytest-timeout \
    pytest-asyncio \
    # Linting & Formatting
    black \
    flake8 \
    pylint \
    mypy \
    isort \
    autopep8 \
    # Type checking
    types-requests \
    types-beautifulsoup4 \
    # Code quality
    bandit \
    safety \
    radon \
    # Pre-commit
    pre-commit \
    # Documentation
    sphinx \
    sphinx-rtd-theme \
    # Debugging
    ipdb \
    ipython \
    # Profiling
    line-profiler \
    memory-profiler \
    # Development utilities
    python-dotenv \
    watchdog

# Install UniDic for Japanese text processing
RUN pip install unidic-lite && \
    python3 -m unidic download

# Switch to non-root user
USER $USERNAME

# Setup workspace
WORKDIR /workspace

# Copy entrypoint script
COPY --chown=$USERNAME:$USERNAME .devcontainer/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN sudo chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["sleep", "infinity"]
