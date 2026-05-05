FROM python:3.10-slim

# Install system dependencies for GUI and Audio
RUN apt-get update && apt-get install -y \
    libgl1 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shm0 \
    libxcb-util1 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libfontconfig1 \
    libice6 \
    libsm6 \
    libxext6 \
    libxrender1 \
    alsa-utils \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DOCKER=1
ENV DISPLAY=host.docker.internal:0
ENV QT_X11_NO_MITSHM=1

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Manually install voicevox-core via .whl (not on PyPI for all archs)
ARG TARGETARCH
RUN if [ "$TARGETARCH" = "arm64" ]; then \
        VV_WHL="https://github.com/VOICEVOX/voicevox_core/releases/download/0.14.4/voicevox_core-0.14.4+cpu-cp38-abi3-linux_aarch64.whl"; \
    else \
        VV_WHL="https://github.com/VOICEVOX/voicevox_core/releases/download/0.14.4/voicevox_core-0.14.4+cpu-cp38-abi3-linux_x86_64.whl"; \
    fi && \
    pip install --no-cache-dir "$VV_WHL"

# Download llama-server binary for Linux (generic x64 or arm64)
RUN if [ "$TARGETARCH" = "arm64" ]; then \
        LLAMA_URL="https://github.com/ggml-org/llama.cpp/releases/download/b8808/llama-b8808-bin-ubuntu-arm64.tar.gz"; \
    else \
        LLAMA_URL="https://github.com/ggml-org/llama.cpp/releases/download/b8808/llama-b8808-bin-ubuntu-x64.tar.gz"; \
    fi && \
    curl -L -o llama.tar.gz "$LLAMA_URL" && \
    mkdir -p llama_bin && \
    tar -xzf llama.tar.gz -C llama_bin && \
    find llama_bin -type f -name "llama-server" -exec mv {} /usr/local/bin/ \; && \
    chmod +x /usr/local/bin/llama-server && \
    rm -rf llama.tar.gz llama_bin

# Copy source code
COPY . .

# Make scripts executable
RUN chmod +x setup_models.sh docker-entrypoint.sh

# Entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]
