#!/bin/bash
set -e

# Detect Architecture
ARCH=$(uname -m)
echo "Detected architecture: $ARCH"

# Create directories
mkdir -p voicevox/models
mkdir -p models

# 1. Handle VoiceVox Libraries
# We check if .so files already exist in voicevox/
if [ -f "voicevox/libvoicevox_core.so" ] && [ -f "voicevox/libvoicevox_onnxruntime.so" ]; then
    echo "✅ Found existing VoiceVox Linux libraries (.so). Skipping download."
else
    echo "Downloading VoiceVox Core (Linux)..."
    if [ "$ARCH" == "arm64" ] || [ "$ARCH" == "aarch64" ]; then
        VV_URL="https://github.com/VOICEVOX/voicevox_core/releases/download/0.14.4/voicevox_core-linux-arm64-cpu-0.14.4.zip"
    else
        VV_URL="https://github.com/VOICEVOX/voicevox_core/releases/download/0.14.4/voicevox_core-linux-x64-cpu-0.14.4.zip"
    fi
    curl -L -o voicevox_core.zip "$VV_URL"
    unzip -o voicevox_core.zip -d voicevox_temp/
    mv voicevox_temp/voicevox_core-linux-*-0.14.4/*.so* voicevox/
    rm -rf voicevox_core.zip voicevox_temp
fi

# 2. Download OpenJTalk Dictionary if missing
if [ ! -d "voicevox/open_jtalk_dic_utf_8-1.11" ]; then
    echo "Downloading OpenJTalk Dictionary..."
    DICT_URL="https://github.com/VOICEVOX/voicevox_core/releases/download/0.14.4/open_jtalk_dic_utf_8-1.11.tar.gz"
    curl -L -o dict.tar.gz "$DICT_URL"
    tar -xzf dict.tar.gz -C voicevox/
    rm dict.tar.gz
fi

# 3. Download Llama-3-8B Instruct GGUF if missing
MODEL_PATH="models/Llama-3-8B-Instruct-Q4_K_M.gguf"
if [ ! -f "$MODEL_PATH" ]; then
    echo "Downloading Llama-3-8B-Instruct-Q4_K_M.gguf..."
    # Using Bartowski's high-quality GGUF release
    MODEL_URL="https://huggingface.co/Bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf"
    curl -L -o "$MODEL_PATH" "$MODEL_URL"
    
    # Symlink or copy to Bonsai-8B.gguf if the code expects that name
    if [ ! -f "models/Bonsai-8B.gguf" ]; then
        ln -s "Llama-3-8B-Instruct-Q4_K_M.gguf" "models/Bonsai-8B.gguf"
    fi
fi

echo "✨ Setup complete!"
