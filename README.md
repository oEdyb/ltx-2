# LTX-2 ASMR Video Production Pipeline

Generate ASMR and ambient YouTube videos using LTX-2 on RunPod with ComfyUI.

**What this is**: Pre-built workflows, prompt templates, and setup scripts to go from text/image to ASMR video clips with synchronized audio — 25x cheaper and 5x faster than Runway.

## Quick Start

### 1. Create a RunPod Pod

1. Go to [runpod.io](https://runpod.io) → GPU Cloud → Deploy
2. Search for the **ComfyUI** template
3. Pick a GPU:
   - **RTX 4090** (~$0.50/hr) — good for most clips
   - **A100 80GB** (~$2/hr) — faster, no VRAM issues
4. Set disk to **100GB+** (models are large)
5. Click Deploy

### 2. Run Setup

Once the pod is running, open a terminal (Connect → Terminal) and run:

```bash
# Download this repo (replace with your actual repo URL)
# git clone https://github.com/YOUR_USERNAME/ltx-2.git /workspace/ltx-2
# Or just upload the files manually via RunPod's file manager

# Run setup (installs nodes + downloads models)
bash /workspace/ltx-2/scripts/setup-runpod.sh
```

This takes ~30 minutes on first run (downloads ~70GB of models). Go grab coffee.

### 3. Load a Workflow

1. Open ComfyUI in your browser (the Connect → HTTP button on RunPod)
2. Click **Load** (top menu)
3. Browse to `custom_nodes/ComfyUI-LTXVideo/example_workflows/asmr/`
4. Open **asmr-txt2vid.json**

### 4. Generate Your First Clip

1. Find the **"Your ASMR Prompt"** node (the big text box)
2. Paste or edit a prompt from `prompts/` (or write your own)
3. Click **Queue Prompt** (or press Enter)
4. Wait ~25-60 seconds → your clip appears in the output

### 5. Download & Edit

1. Right-click the SaveVideo node → Open in new tab → Download
2. Import into CapCut or DaVinci Resolve
3. Chain multiple clips together
4. Add background music if needed (YouTube Audio Library)
5. Export at **1440p** H.264 for YouTube (triggers VP9 codec = better quality)

---

## Workflows

| File | What It Does | When to Use |
|------|-------------|-------------|
| `asmr-txt2vid.json` | Text prompt → video + audio | Starting from scratch with a text idea |
| `asmr-img2vid.json` | Image + prompt → video + audio | Animating a NanoBanana/Midjourney image |

Both workflows include:
- **Static camera LoRA** pre-loaded (perfect for ASMR)
- **Prompt enhancer** that adds audio detail automatically
- **Spatial upscaler** (2x resolution built into the pipeline)
- **Audio generation** (rain, fire, ambient sounds — built into LTX-2)

### Creating Extend & Upscale Workflows

For clip extension and standalone upscaling, the best approach is to modify the official workflows in ComfyUI:

**Extending clips (making longer videos):**
1. Load the official `LTX-2_T2V_Distilled_wLora.json`
2. Add an `LTXVExtendSampler` node after the first generation
3. Connect the latent output → `LTXVExtendSampler` → VAE Decode → Save
4. Set `num_new_frames: 80`, `frame_overlap: 16`, `strength: 0.5`

**Standalone upscaling:**
The spatial upscaler is already built into both ASMR workflows (the `LatentUpscaleModelLoader` node). The two-stage sampler handles upscaling automatically.

---

## Prompt Templates

Ready-to-use prompts in the `prompts/` folder:

| File | Scenes |
|------|--------|
| `asmr-rain.txt` | Window rain, forest rain, puddle reflections, tin roof, car window |
| `asmr-nature.txt` | Forest stream, autumn leaves, fireplace, meadow, snow, waterfall |
| `asmr-cozy.txt` | Candle reading, morning coffee, blankets, fairy lights, writing desk, cat |
| `asmr-ocean.txt` | Beach waves, tide pools, sunset, coral reef, night beach, driftwood |

Each prompt follows the LTX-2 prompting best practices:
- Single flowing paragraph, present tense
- 4-8 sentences covering visuals + camera + audio
- Specific audio descriptions (not "rain sounds" but "gentle rain tapping against frosted glass")
- Static or slow camera movement by default

### Writing Your Own Prompts

**Do:**
- Start with `Style: cinematic-realistic` (or your preferred style)
- Describe scene → action → audio in chronological flow
- Use present-progressive verbs: "is falling", "crackling softly"
- Be specific about audio: "soft footsteps on wet cobblestone"
- Keep camera static or very slow for ASMR

**Don't:**
- Use emotional labels without visual descriptions
- Try to generate readable text or logos
- Overload scenes with too many subjects
- Add complex physics (jumping, juggling)
- Conflict light sources without reason

---

## Settings Guide

### Frame Count (how long is the clip)

Must follow the formula: `8n + 1`

| Frames | Duration (24fps) | Duration (25fps) | Best For |
|--------|-------------------|-------------------|----------|
| 33 | 1.4s | 1.3s | Quick test |
| 65 | 2.7s | 2.6s | Standard clip |
| 97 | 4.0s | 3.9s | Longer scene |
| 121 | 5.0s | 4.8s | Extended scene |

### Resolution

Must be divisible by 64. The spatial upscaler doubles it.

| Base Resolution | After 2x Upscale | Aspect Ratio |
|-----------------|-------------------|--------------|
| 768 x 512 | 1536 x 1024 | 3:2 (landscape) |
| 512 x 768 | 1024 x 1536 | 2:3 (portrait) |
| 768 x 448 | 1536 x 896 | ~16:9 |
| 576 x 320 | 1152 x 640 | 16:9 (fast draft) |

For YouTube ASMR: use **768 x 448** base (becomes ~1536 x 896 after upscale, close to 1440p).

### Model Selection

| Model | Steps | Speed | Quality | When |
|-------|-------|-------|---------|------|
| `ltx-2-19b-distilled.safetensors` | 8 | Fast (~25s) | Good | Drafts, iteration |
| `ltx-2-19b-dev-fp8.safetensors` | 20-40 | Slow (~2min) | Best | Final renders |

The workflows default to the distilled model. To switch: change the model name in the `CheckpointLoaderSimple` node.

### Camera LoRAs

Pre-loaded: **Static** (ideal for ASMR). To change, swap the LoRA file in the "Camera LoRA" node:

| LoRA | Effect |
|------|--------|
| `camera-control-static` | No camera movement (default for ASMR) |
| `camera-control-dolly-in` | Slow zoom in |
| `camera-control-dolly-out` | Slow zoom out |
| `camera-control-dolly-left` | Slow pan left |
| `camera-control-dolly-right` | Slow pan right |
| `camera-control-jib-up` | Slow tilt up |
| `camera-control-jib-down` | Slow tilt down |

---

## Cost Estimate

| Task | GPU | Time | Cost |
|------|-----|------|------|
| 1 ASMR clip (2.7s) | RTX 4090 | ~30s | ~$0.004 |
| 10 clips for a video | RTX 4090 | ~5 min | ~$0.04 |
| Full 2-hour session | RTX 4090 | 2 hrs | ~$1.00 |
| **1 minute ASMR video** | RTX 4090 | ~15 min | ~$0.12 |

Compare: Runway charges ~$0.50 per 4s clip = $7.50 for the same 1-minute video.

---

## Project Structure

```
ltx-2/
  README.md                          # This file
  workflows/                         # ComfyUI workflow JSONs
    asmr-txt2vid.json                #   Text → video + audio
    asmr-img2vid.json                #   Image → video + audio
  prompts/                           # Prompt templates
    asmr-rain.txt                    #   Rain scenes
    asmr-nature.txt                  #   Nature / forest / fire
    asmr-cozy.txt                    #   Cozy indoor scenes
    asmr-ocean.txt                   #   Ocean / beach scenes
  scripts/                           # Setup & utilities
    setup-runpod.sh                  #   Full RunPod setup
    download-models.sh               #   Standalone model download
    generate_workflows.py            #   Workflow JSON generator
  src/                               # Phase 2 (planned, not yet created)
    batch_generate.py                #   (planned) ComfyUI API batch generator
    assemble.py                      #   (planned) Video assembly
    app.py                           #   (planned) Gradio web UI
```

---

## Models Downloaded

The setup script downloads these automatically:

| Model | Size | Location |
|-------|------|----------|
| `ltx-2-19b-distilled.safetensors` | ~38GB | `models/checkpoints/` |
| `ltx-2-19b-dev-fp8.safetensors` | ~19GB | `models/checkpoints/` |
| `ltx-2-spatial-upscaler-x2-1.0.safetensors` | ~2GB | `models/latent_upscale_models/` |
| `ltx-2-temporal-upscaler-x2-1.0.safetensors` | ~2GB | `models/latent_upscale_models/` |
| `ltx-2-19b-distilled-lora-384.safetensors` | ~1GB | `models/loras/` |
| `camera-control-static LoRA` | ~200MB | `models/loras/` |
| `gemma-3-12b-it (text encoder)` | ~7GB | `models/text_encoders/` |

Total: ~70GB

---

## Troubleshooting

**"Missing node" error when loading workflow**
- Make sure ComfyUI-LTXVideo is installed. Run the setup script again.
- For `CM_FloatToInt`: install ComfyMath (`ComfyUI/custom_nodes/ComfyMath`).

**Out of VRAM**
- Reduce resolution (try 576x320 base)
- Reduce frame count (try 33 frames)
- Use FP8 model variant instead of BF16
- Use `LowVRAMCheckpointLoader` nodes instead of standard loaders

**No audio in output**
- Make sure `LTXVAudioVAELoader` is connected to the sampler
- Check that `CreateVideo` has the audio input connected
- Audio is generated jointly — if the prompt describes sounds, they should appear

**Workflow doesn't match expected nodes**
- The sampler nodes use UUID-based type IDs (this is normal for ComfyUI v3 nodes)
- If you see UUID errors, update ComfyUI and the LTXVideo extension to latest

**Models not loading**
- Verify files are in the correct directories (see Models table above)
- Re-run `scripts/download-models.sh` if files are missing or corrupted

---

## Phase 2 (Future)

When manual clip generation is running smoothly, we'll add:

1. **`batch_generate.py`** — Python script that calls ComfyUI's REST API to queue multiple scenes from a JSON scene list
2. **`assemble.py`** — Auto-stitches clips with crossfade transitions + audio layering
3. **`app.py`** — Simple Gradio web UI: paste a concept → auto-generates scene prompts → batch generates → assembles → outputs YouTube-ready video

---

## Links

- [LTX-2 Model](https://huggingface.co/Lightricks/LTX-2)
- [ComfyUI-LTXVideo Nodes](https://github.com/Lightricks/ComfyUI-LTXVideo)
- [LTX-2 Prompting Guide](https://ltx.io/model/model-blog/prompting-guide-for-ltx-2)
- [LTX-2 ComfyUI Docs](https://docs.ltx.video/open-source-model/integration-tools/comfy-ui)
- [RunPod](https://runpod.io)
