#!/usr/bin/env bash
# =============================================================================
# LTX-2 ASMR Pipeline -- RunPod Setup Script
# =============================================================================
# Run this on a fresh RunPod ComfyUI pod to install LTX-2 custom nodes and
# download all required models. Designed for RunPod's ComfyUI template.
#
# Usage:
#   bash setup-runpod.sh
#
# Requirements:
#   - RunPod GPU Pod with ComfyUI template (RTX 4090 or A100 recommended)
#   - ~100GB free disk space for models
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log()  { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[x]${NC} $1"; }
info() { echo -e "${BLUE}[>]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------- Detect ComfyUI location ----------

COMFYUI_ROOT=""
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

if [ -z "$COMFYUI_ROOT" ]; then
    err "Could not find ComfyUI installation. Searched:"
    err "  /workspace/runpod-slim/ComfyUI, /workspace/ComfyUI, /opt/ComfyUI, /root/ComfyUI, ~/ComfyUI"
    err "Set COMFYUI_ROOT manually and re-run."
    exit 1
fi

log "Found ComfyUI at: $COMFYUI_ROOT"

# ---------- Install custom nodes ----------

CUSTOM_NODES="$COMFYUI_ROOT/custom_nodes"

install_custom_node() {
    local repo_url="$1"
    local dir_name="$2"
    local desc="$3"
    local node_dir="$CUSTOM_NODES/$dir_name"

    if [ -d "$node_dir" ]; then
        log "$desc already present."
    else
        info "Installing $desc..."
        git clone "$repo_url" "$node_dir"
        log "$desc installed."
    fi
}

# ComfyUI-LTXVideo (with update + pip install)
LTXV_DIR="$CUSTOM_NODES/ComfyUI-LTXVideo"
if [ -d "$LTXV_DIR" ]; then
    info "ComfyUI-LTXVideo already installed, updating..."
    cd "$LTXV_DIR" && git pull
else
    info "Installing ComfyUI-LTXVideo custom nodes..."
    git clone https://github.com/Lightricks/ComfyUI-LTXVideo.git "$LTXV_DIR"
fi
info "Installing Python dependencies..."
pip install -r "$LTXV_DIR/requirements.txt"
log "ComfyUI-LTXVideo nodes installed."

# ComfyUI-Manager is pre-installed in the RunPod ComfyUI template.
# If missing for some reason, the install_custom_node helper can add it.

install_custom_node "https://github.com/evanspearman/ComfyMath.git" \
    "ComfyMath" "ComfyMath (required for CM_FloatToInt node)"

# ---------- Download models (delegates to download-models.sh) ----------

info "Downloading LTX-2 models (this takes a while)..."
bash "$SCRIPT_DIR/download-models.sh" "$COMFYUI_ROOT"

# ---------- Copy our custom workflows ----------

info "Setting up ASMR workflows..."
WORKFLOWS_SRC="$SCRIPT_DIR/../workflows"
WORKFLOWS_DST="$COMFYUI_ROOT/custom_nodes/ComfyUI-LTXVideo/example_workflows/asmr"

if [ -d "$WORKFLOWS_SRC" ]; then
    mkdir -p "$WORKFLOWS_DST"
    cp "$WORKFLOWS_SRC"/*.json "$WORKFLOWS_DST/" 2>/dev/null || true
    log "ASMR workflows copied to: $WORKFLOWS_DST"
else
    warn "Workflows directory not found at $WORKFLOWS_SRC -- skip copying."
fi

# ---------- Summary ----------

echo ""
echo "=============================================="
echo -e "${GREEN}  LTX-2 ASMR Setup Complete!${NC}"
echo "=============================================="
echo ""
echo "  ComfyUI:    $COMFYUI_ROOT"
echo "  Nodes:      $LTXV_DIR"
echo ""
echo "  Next steps:"
echo "    1. Restart ComfyUI (or reload the page)"
echo "    2. Click Load > browse to example_workflows/asmr/"
echo "    3. Start with asmr-txt2vid.json"
echo ""
