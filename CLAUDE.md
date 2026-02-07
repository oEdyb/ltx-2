# CLAUDE.md — LTX-2 ASMR Video Production Pipeline

## What This Project Is

An ASMR/ambient YouTube video production pipeline using LTX-2 (open-source video+audio generation model) on RunPod cloud GPUs via ComfyUI. Built for a non-technical user who generates images on NanoBanana and wants to turn them into ASMR video clips.

**Primary user**: Non-technical (comfortable with web UIs, not CLI).
**Hardware**: No local GPU capable of running LTX-2. Everything runs on RunPod.
**Current phase**: Phase 1 (manual ComfyUI workflows). Phase 2 (Python automation) is planned but not built.

## Project Structure

```
ltx-2/
  CLAUDE.md                          # This file
  README.md                          # User-facing setup & usage guide
  workflows/
    asmr-txt2vid.json                # Text → video + audio (ComfyUI workflow)
    asmr-img2vid.json                # Image → video + audio (ComfyUI workflow)
  prompts/
    asmr-rain.txt                    # 6 rain scene prompts
    asmr-nature.txt                  # 6 nature scene prompts
    asmr-cozy.txt                    # 6 cozy indoor prompts
    asmr-ocean.txt                   # 6 ocean/beach prompts
  scripts/
    setup-runpod.sh                  # Full RunPod pod setup (nodes + models)
    download-models.sh               # Standalone model downloader
    generate_workflows.py            # Python script that generates the workflow JSONs
  src/                               # Phase 2 (empty, planned)
```

## Architecture Overview

```
Phase 1 (now):   ComfyUI on RunPod → Manual workflow → Export clips → Edit in CapCut/DaVinci
Phase 2 (later): Python batch script → ComfyUI API → Auto-assembly → Simple web UI
```

ComfyUI workflows are JSON files. We design them visually in ComfyUI, but they can be automated via ComfyUI's REST API later. This gives a visual tool now and a programmable backend later.

---

## LTX-2 Technical Reference

### Model Architecture
- **19B parameter** joint audio-video diffusion transformer
  - 14B parameters for video, 5B for audio
  - Generates synchronized audio+video in a single pass
- Made by Lightricks (open-source, Apache 2.0)
- HuggingFace: https://huggingface.co/Lightricks/LTX-2

### Model Variants

| File | Location | Purpose |
|------|----------|---------|
| `ltx-2-19b-distilled.safetensors` (~38GB) | `models/checkpoints/` | Fast drafts, **8 steps**, CFG=1 |
| `ltx-2-19b-distilled-fp8.safetensors` (~19GB) | `models/checkpoints/` | Same but FP8 quantized, less VRAM |
| `ltx-2-19b-dev.safetensors` (~38GB) | `models/checkpoints/` | Quality renders, **20-40 steps**, CFG=3.5-5.0 |
| `ltx-2-19b-dev-fp8.safetensors` (~19GB) | `models/checkpoints/` | Same but FP8 quantized |
| `ltx-2-spatial-upscaler-x2-1.0.safetensors` | `models/latent_upscale_models/` | 2x resolution in latent space |
| `ltx-2-temporal-upscaler-x2-1.0.safetensors` | `models/latent_upscale_models/` | 2x frame rate in latent space |
| `ltx-2-19b-distilled-lora-384.safetensors` | `models/loras/` | Distilled LoRA (apply to dev model) |
| Camera LoRAs (static, dolly-in, etc.) | `models/loras/` | Camera motion control |
| `gemma-3-12b-it-qat-q4_0-unquantized/` | `models/text_encoders/` | Gemma 3 text encoder (~7GB) |

### Generation Constraints
- **Frame count**: Must be `8n + 1` → valid: 9, 17, 25, 33, 41, 49, 57, 65, 73, 81, 89, 97, 105, 113, 121
- **Width/Height**: Must be divisible by **64** (the docs say 32, but 64 gives best results)
- **Invalid params don't error** — ComfyUI silently rounds to nearest valid value
- At 24fps: 65 frames = ~2.7s, 97 frames = ~4s, 121 frames = ~5s

### Two-Stage Pipeline
The production approach is two stages:
1. **Stage 1**: Generate at low resolution (e.g., 768x512) with the main model
2. **Stage 2**: Upscale 2x in latent space using the spatial upscaler (→ 1536x1024)

Both our workflows include this automatically via the UUID sampler nodes.

---

## ComfyUI-LTXVideo Nodes

### Source
- GitHub: https://github.com/Lightricks/ComfyUI-LTXVideo
- Official docs: https://docs.ltx.video/open-source-model/integration-tools/comfy-ui

### Critical: UUID-Based Sampler Nodes
The LTX-2 sampler nodes are **ComfyUI v3 nodes** with UUID-based type IDs (not human-readable names):

| UUID | Node | Purpose |
|------|------|---------|
| `61915fab-cab7-41be-9727-d69a7e41f24a` | T2V Two-Stage Sampler | Text-to-video with built-in upscaling + audio |
| `3eaa20c4-5842-4fe4-87df-c0a7e83a6a78` | I2V Two-Stage Sampler | Image-to-video with built-in upscaling + audio |

These UUIDs are **stable across installations** (they're defined in the node schema, not generated per-instance).

### T2V Sampler Inputs (10 slots)
| Slot | Label | Type |
|------|-------|------|
| 0 | model stage 1 | MODEL |
| 1 | model stage 2 | MODEL |
| 2 | upscale model | LATENT_UPSCALE_MODEL |
| 3 | positive | CONDITIONING |
| 4 | negative | CONDITIONING |
| 5 | VAE | VAE |
| 6 | audio vae | VAE |
| 7 | empty latent image | IMAGE |
| 8 | length | INT |
| 9 | frame rate | INT |

Widget values: `[length, frame_rate, seed]`

### I2V Sampler Inputs (12 slots)
| Slot | Label | Type |
|------|-------|------|
| 0 | model stage 1 | MODEL |
| 1 | model stage 2 | MODEL |
| 2 | upscale model | LATENT_UPSCALE_MODEL |
| 3 | positive | CONDITIONING |
| 4 | negative | CONDITIONING |
| 5 | images (conditioning) | IMAGE |
| 6 | vae | VAE |
| 7 | audio vae | VAE |
| 8 | empty latent image | IMAGE |
| 9 | length | INT |
| 10 | frame rate | INT |
| 11 | image strength | FLOAT |

Widget values: `[length, frame_rate, strength, seed]`

### Other Key Nodes (from ComfyUI-LTXVideo)
- `LTXVGemmaCLIPModelLoader` — Loads Gemma 3 text encoder + LTX checkpoint
- `LTXVGemmaEnhancePrompt` — AI prompt enhancement (has separate T2V/I2V system prompts)
- `LTXVAudioVAELoader` — Loads audio VAE (uses same checkpoint file as main model)
- `LTXVConditioning` — Wraps conditioning with frame rate info
- `LTXVBaseSampler` — Lower-level sampler (width/height/num_frames explicit)
- `LTXVExtendSampler` — Video continuation (num_new_frames, frame_overlap, strength)
- `LTXVLoopingSampler` — Long video generation with temporal tiling
- `LTXVTiledSampler` — Spatial + temporal tiled sampling for large videos
- `LTXVAddGuideAdvanced` — Image conditioning for I2V (frame_idx, strength, crf, blur)
- `STGGuiderAdvancedNode` — Dynamic per-sigma CFG+STG guidance
- `LTXVLinearOverlapLatentTransition` — Blend two video latents for transitions
- `LowVRAMCheckpointLoader` / `LowVRAMAudioVAELoader` — For 32GB VRAM systems

### Nodes from ComfyUI Core (used in workflows)
- `CheckpointLoaderSimple` — Loads .safetensors checkpoint
- `CLIPTextEncode` — Standard text encoding
- `LoraLoaderModelOnly` — Loads LoRA into model
- `LatentUpscaleModelLoader` — Loads spatial/temporal upscaler
- `EmptyImage` — Creates blank image (sets resolution for generation)
- `CreateVideo` — Combines images + audio into video
- `SaveVideo` — Saves video to disk
- `PrimitiveStringMultiline` / `PrimitiveInt` / `PrimitiveFloat` — UI input nodes
- `CM_FloatToInt` — Float→Int conversion (requires **ComfyMath** custom nodes)
- `LoadImage` — Loads user-uploaded image
- `MarkdownNote` — Documentation/instructions in workflow

### Official Example Workflows (in the repo)
Located at `ComfyUI/custom_nodes/ComfyUI-LTXVideo/example_workflows/`:
- `LTX-2_T2V_Full_wLora.json` — T2V with dev model
- `LTX-2_T2V_Distilled_wLora.json` — T2V with distilled model (fast)
- `LTX-2_I2V_Full_wLora.json` — I2V with dev model
- `LTX-2_I2V_Distilled_wLora.json` — I2V with distilled model (fast)
- `LTX-2_V2V_Detailer.json` — Video-to-video detailer
- `LTX-2_ICLoRA_All_Distilled.json` — IC-LoRA (depth + pose + edges)

---

## Workflow JSON Format

ComfyUI workflows are node graphs serialized as JSON. Key structure:

```json
{
  "id": "uuid",
  "last_node_id": 51,
  "last_link_id": 24,
  "nodes": [
    {
      "id": 1,
      "type": "CheckpointLoaderSimple",  // or UUID for v3 nodes
      "pos": [-3200, 0],
      "size": [400, 100],
      "mode": 0,                          // 0=active, 4=bypassed
      "inputs": [{"name": "...", "type": "MODEL", "link": 5}],
      "outputs": [{"name": "MODEL", "type": "MODEL", "links": [1, 2]}],
      "widgets_values": ["ltx-2-19b-distilled.safetensors"],
      "properties": {"Node name for S&R": "CheckpointLoaderSimple"}
    }
  ],
  "links": [
    // [link_id, source_node_id, source_slot, dest_node_id, dest_slot, data_type]
    [1, 1, 0, 5, 0, "MODEL"]
  ]
}
```

### WorkflowBuilder Pattern
We generate workflows with `scripts/generate_workflows.py` using a `WorkflowBuilder` class that:
- Stores nodes by ID (not array index — avoids off-by-one bugs)
- `connect(src_id, src_slot, dst_id, dst_slot, dtype)` updates both source output links and dest input link atomically
- `build()` exports the final JSON

This is much safer than hand-editing JSON where one wrong link ID silently breaks everything.

---

## Our ASMR Workflow Customizations

Both `asmr-txt2vid.json` and `asmr-img2vid.json` differ from the official examples:

1. **ASMR-specific prompt enhancer system prompts** — Custom instructions in the `LTXVGemmaEnhancePrompt` node that bias toward:
   - Rich ambient audio descriptions (rain, fire, water, wind)
   - Static or very slow camera movement
   - Calm, contemplative, meditative atmospheres
   - Present-progressive verbs and chronological flow

2. **Static camera LoRA pre-loaded** — `ltx-2-19b-lora-camera-control-static.safetensors` at strength 1.0

3. **Second LoRA slot (bypassed)** — Ready for style LoRAs, user enables with Ctrl+B

4. **768x512 base resolution** — Upscales to 1536x1024 via spatial upscaler

5. **65 frames at 24fps** — ~2.7s clips (good balance of quality and speed)

6. **ASMR default prompts** — Rainy window scene (T2V) / candlelight motion (I2V)

---

## Prompting Guide for LTX-2

Source: https://ltx.io/model/model-blog/prompting-guide-for-ltx-2

### Best Practices
- Write as a **single flowing paragraph** in **present tense**
- **4-8 sentences** covering: shot type → scene setting → action → audio
- Be specific about audio: "gentle rain tapping against frosted glass" not "rain sounds"
- Use camera language: "static", "slow dolly in", "handheld tracking"
- Include style prefix: `Style: cinematic-realistic, ...`

### What Works Well
- Single-subject shots with thoughtful lighting
- Atmospheric elements: fog, mist, golden hour, rain, reflections
- Backlighting, color palettes, shallow depth of field
- Characters speaking/singing in various languages

### What to Avoid
- Emotional labels without visual descriptions (say "shoulders slumped" not "sad")
- Text and logos (LTX-2 can't generate readable text)
- Complex non-linear physics (jumping, juggling)
- Scene overload (too many characters/actions)
- Conflicting light sources

---

## Gotchas & Lessons Learned

1. **Gemma 3 requires HF auth** — Users need to accept the license at https://huggingface.co/google/gemma-3-12b-it-qat-q4_0-unquantized and run `hf auth login` before downloading.

2. **ComfyUI workflow JSON is fragile** — One wrong link ID breaks everything silently. Always use the `WorkflowBuilder` class pattern instead of manual JSON editing.

3. **CM_FloatToInt requires ComfyMath** — This is a separate custom node package (`ComfyMath`), not part of ComfyUI core or LTXVideo. Setup script installs it.

4. **UUID sampler nodes vs named nodes** — The two-stage sampler nodes use UUIDs because they're v3 nodes. If these UUIDs change in a future update, workflows break. Pin the ComfyUI-LTXVideo version if stability matters.

5. **Invalid frame count/resolution doesn't error** — ComfyUI silently rounds to nearest valid value. This can cause unexpected clip lengths.

6. **FP8 vs BF16** — FP8 is ~30% smaller with minimal quality loss. Use FP8 for iteration, BF16 for final quality (if you have the VRAM).

7. **Distilled model uses CFG=1** — Do NOT increase CFG for the distilled model; it was trained without classifier-free guidance. Dev model uses CFG=3.5-5.0.

8. **Audio VAE loads the same checkpoint** — `LTXVAudioVAELoader` takes the same `.safetensors` file as `CheckpointLoaderSimple`. It extracts the audio VAE weights from the unified model.

9. **LoRA mode=4 means bypassed** — In ComfyUI JSON, `"mode": 4` bypasses the node. `"mode": 0` is active.

10. **Spatial upscaler goes in `latent_upscale_models/`** — NOT in `checkpoints/`. This is a common mistake.

11. **HuggingFace CLI command varies by environment** — Older installs have `huggingface-cli`, newer ones (RunPod, huggingface_hub v1.0+) use `hf`. Our download script auto-detects which is available. The `hf` subcommands differ slightly: `hf auth login` (not `hf login`), `hf download` (same args as `huggingface-cli download`).

12. **`--local-dir-use-symlinks` is removed** — Deprecated and deleted in huggingface_hub v1.0+. Just use `--local-dir` alone. The new download system handles everything without symlinks.

13. **RunPod ComfyUI template path is `/workspace/runpod-slim/ComfyUI`** — NOT `/workspace/ComfyUI`. The `runpod/comfyui:latest` template uses this non-obvious path. Both scripts auto-detect it.

14. **RunPod ComfyUI template pre-installs ComfyUI-Manager** — No need to install it again. Also includes ComfyUI-KJNodes and Civicomfy. We only need to add ComfyUI-LTXVideo and ComfyMath.

15. **RunPod `python` is not in PATH** — Use `python3` instead, or call modules directly. The `hf` command works but `huggingface-cli` does not.

16. **Private GitHub repos need auth on RunPod** — RunPod pods don't have your GitHub credentials. Either make the repo public or set up a personal access token. We made it public since it contains no secrets.

17. **A40 is better value than RTX 4090 for LTX-2** — A40 has 48GB VRAM ($0.40/hr) vs 4090's 24GB ($0.59/hr). The BF16 distilled model (~38GB) won't fit on a 4090 — you'd need the FP8 version. A40 runs everything without VRAM constraints. It's slower per clip (~45-60s vs ~25s) but cheaper per hour.

---

## RunPod Deployment Reference

### Template & GPU
- **Template**: `runpod/comfyui:latest` (official ComfyUI template)
- **Recommended GPU**: A40 (48GB VRAM, $0.40/hr) — runs all model variants
- **Alternative GPU**: RTX 4090 (24GB VRAM, $0.59/hr) — faster but FP8 models only
- **Volume Disk**: 150 GB (models are ~70GB, need headroom)

### Paths on RunPod
- ComfyUI install: `/workspace/runpod-slim/ComfyUI`
- ComfyUI args: `/workspace/runpod-slim/comfyui_args.txt`
- Our repo: `/workspace/ltx-2` (after git clone)
- ASMR workflows (after setup): `/workspace/runpod-slim/ComfyUI/custom_nodes/ComfyUI-LTXVideo/example_workflows/asmr/`

### Ports
- **8188**: ComfyUI web UI
- **8080**: FileBrowser (login: `admin` / `adminadmin12`)
- **8888**: JupyterLab
- **22**: SSH (needs PUBLIC_KEY in env vars)

### Billing
- Running: ~$0.43/hr (GPU + disk)
- Stopped: ~$0.014/hr (disk storage only, ~$10/month)
- Terminated: $0 (everything deleted)
- **Always Stop the pod when done generating.** Don't leave it running.

### Setup Commands (run in terminal after pod boots)
```bash
git clone https://github.com/oEdyb/ltx-2.git /workspace/ltx-2
hf auth login                    # paste HuggingFace token
bash /workspace/ltx-2/scripts/setup-runpod.sh   # ~30 min first time
```

### GitHub Repo
- **URL**: https://github.com/oEdyb/ltx-2 (public)
- Push updates locally, `git pull` on RunPod to sync

---

## Phase 2 Plans (Not Built Yet)

1. **`src/batch_generate.py`** — Reads scene list (JSON/CSV), calls ComfyUI REST API, queues all scenes, monitors via WebSocket, downloads clips
2. **`src/assemble.py`** — Stitches clips with crossfade transitions, layers audio, exports YouTube-ready MP4 (MoviePy)
3. **`src/app.py`** — Gradio web UI: paste concept → generate scene prompts → batch queue → preview → assemble

ComfyUI's API is at `http://localhost:8188/prompt` (POST workflow JSON) and WebSocket at `ws://localhost:8188/ws` for progress.

---

## Key Links

- **LTX-2 Model**: https://huggingface.co/Lightricks/LTX-2
- **ComfyUI-LTXVideo**: https://github.com/Lightricks/ComfyUI-LTXVideo
- **LTX-2 Main Repo**: https://github.com/Lightricks/LTX-2
- **LTX-2 Pipelines README**: https://github.com/Lightricks/LTX-2/blob/main/packages/ltx-pipelines/README.md
- **Prompting Guide**: https://ltx.io/model/model-blog/prompting-guide-for-ltx-2
- **ComfyUI Docs for LTX-2**: https://docs.ltx.video/open-source-model/integration-tools/comfy-ui
- **Gemma 3 Text Encoder**: https://huggingface.co/google/gemma-3-12b-it-qat-q4_0-unquantized
- **Camera LoRAs Collection**: https://huggingface.co/collections/Lightricks/ltx-2
- **RunPod**: https://runpod.io
- **LTX-2 Technical Paper**: https://videos.ltx.io/LTX-2/grants/LTX_2_Technical_Report_compressed.pdf
