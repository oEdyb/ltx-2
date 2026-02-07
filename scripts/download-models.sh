#!/usr/bin/env bash
# =============================================================================
# LTX-2 Model Downloader — Standalone
# =============================================================================
# Downloads LTX-2 model files to a specified directory (or current directory).
# Can be run independently of setup-runpod.sh when you already have ComfyUI.
#
# Usage:
#   bash download-models.sh [COMFYUI_ROOT]
#
# If COMFYUI_ROOT is not provided, it will be auto-detected.
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; }
info() { echo -e "${BLUE}[→]${NC} $1"; }

# ---------- Find ComfyUI root ----------

COMFYUI_ROOT="${1:-}"

if [ -z "$COMFYUI_ROOT" ]; then
    for candidate in \
        /workspace/runpod-slim/ComfyUI \
        /workspace/ComfyUI \
        /opt/ComfyUI \
        /root/ComfyUI \
        "$HOME/ComfyUI"; do
        if [ -d "$candidate" ]; then
            COMFYUI_ROOT="$candidate"
            break
        fi
    done
fi

if [ -z "$COMFYUI_ROOT" ]; then
    err "Could not find ComfyUI. Pass the path as an argument:"
    err "  bash download-models.sh /path/to/ComfyUI"
    exit 1
fi

log "ComfyUI root: $COMFYUI_ROOT"

# ---------- Detect HuggingFace CLI command ----------

HF_CMD=""
if command -v huggingface-cli &> /dev/null; then
    HF_CMD="huggingface-cli"
elif command -v hf &> /dev/null; then
    HF_CMD="hf"
else
    info "Installing huggingface_hub CLI..."
    pip install -U huggingface_hub[cli]
    if command -v huggingface-cli &> /dev/null; then
        HF_CMD="huggingface-cli"
    elif command -v hf &> /dev/null; then
        HF_CMD="hf"
    else
        err "Could not find huggingface CLI after install. Try: pip install -U huggingface_hub"
        exit 1
    fi
fi
log "Using HuggingFace CLI: $HF_CMD"

# ---------- Directories ----------

CHECKPOINTS="$COMFYUI_ROOT/models/checkpoints"
UPSCALE="$COMFYUI_ROOT/models/latent_upscale_models"
LORAS="$COMFYUI_ROOT/models/loras"
TEXT_ENC="$COMFYUI_ROOT/models/text_encoders"

mkdir -p "$CHECKPOINTS" "$UPSCALE" "$LORAS" "$TEXT_ENC"

# ---------- Download function ----------

download_hf() {
    local repo="$1"
    local file="$2"
    local dest="$3"
    local desc="$4"

    if [ -f "$dest/$file" ]; then
        log "$desc — already present"
        return
    fi

    info "Downloading $desc..."
    $HF_CMD download "$repo" "$file" \
        --local-dir "$dest" \
        --local-dir-use-symlinks False
    log "$desc — done"
}

# ---------- Core models ----------

echo ""
echo "=== Checkpoints ==="

download_hf "Lightricks/LTX-2" \
    "ltx-2-19b-distilled.safetensors" \
    "$CHECKPOINTS" \
    "Distilled model (fast, 8 steps, ~38GB)"

download_hf "Lightricks/LTX-2" \
    "ltx-2-19b-dev-fp8.safetensors" \
    "$CHECKPOINTS" \
    "Dev FP8 model (quality, 20-40 steps, ~19GB)"

echo ""
echo "=== Upscalers ==="

download_hf "Lightricks/LTX-2" \
    "ltx-2-spatial-upscaler-x2-1.0.safetensors" \
    "$UPSCALE" \
    "Spatial upscaler (2x resolution)"

download_hf "Lightricks/LTX-2" \
    "ltx-2-temporal-upscaler-x2-1.0.safetensors" \
    "$UPSCALE" \
    "Temporal upscaler (2x FPS)"

echo ""
echo "=== LoRAs ==="

download_hf "Lightricks/LTX-2" \
    "ltx-2-19b-distilled-lora-384.safetensors" \
    "$LORAS" \
    "Distilled LoRA (two-stage pipeline)"

download_hf "Lightricks/LTX-2-19b-LoRA-Camera-Control-Static" \
    "ltx-2-19b-lora-camera-control-static.safetensors" \
    "$LORAS" \
    "Camera Control LoRA — Static (ASMR)"

echo ""
echo "=== Text Encoder ==="

GEMMA_DIR="$TEXT_ENC/gemma-3-12b-it-qat-q4_0-unquantized"
GEMMA_CHECK_FILE="$GEMMA_DIR/model-00001-of-00005.safetensors"
if [ -f "$GEMMA_CHECK_FILE" ]; then
    log "Gemma 3 text encoder — already present"
else
    info "Downloading Gemma 3 12B text encoder (~7GB)..."
    info "(If this fails, you may need to run: hf auth login)"
    $HF_CMD download google/gemma-3-12b-it-qat-q4_0-unquantized \
        --local-dir "$GEMMA_DIR" \
        --local-dir-use-symlinks False
    log "Gemma 3 text encoder — done"
fi

# ---------- Verify ----------

echo ""
echo "=============================================="
echo -e "${GREEN}  Model download complete!${NC}"
echo "=============================================="
echo ""
echo "  Directory sizes:"
du -sh "$CHECKPOINTS" 2>/dev/null || true
du -sh "$UPSCALE" 2>/dev/null || true
du -sh "$LORAS" 2>/dev/null || true
du -sh "$TEXT_ENC" 2>/dev/null || true
echo ""
