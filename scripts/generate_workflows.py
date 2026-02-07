#!/usr/bin/env python3
"""
Generate ASMR-optimized ComfyUI workflow JSONs for LTX-2.

Based on official Lightricks/ComfyUI-LTXVideo example workflows, adapted with:
- ASMR-friendly default prompts and settings
- Static camera LoRA pre-wired
- Audio-aware prompt enhancement system prompts
- Pre-configured for 768x512 base (upscales to ~1536x1024 with spatial upscaler)
"""

import json
import uuid
from pathlib import Path

WORKFLOWS_DIR = Path(__file__).parent.parent / "workflows"

# LTX-2 specific UUIDs for ComfyUI v3 sampler nodes
T2V_SAMPLER_UUID = "61915fab-cab7-41be-9727-d69a7e41f24a"
I2V_SAMPLER_UUID = "3eaa20c4-5842-4fe4-87df-c0a7e83a6a78"

# ASMR prompt enhancer system prompts
T2V_ENHANCER_SYSTEM = (
    "You are a Creative Assistant specializing in ASMR and ambient video content. "
    "Given a user's raw input prompt, expand it into a detailed video generation prompt "
    "with rich visuals and immersive audio.\n\n"
    "#### Guidelines\n"
    "- Strictly follow all aspects of the user's raw input.\n"
    "- If the input is vague, invent concrete details: lighting, textures, materials, atmospheric elements.\n"
    "- Emphasize ambient audio: rain, wind, crackling fire, rustling leaves, flowing water, soft footsteps.\n"
    "- Use active language: present-progressive verbs (\"is falling,\" \"crackling softly\").\n"
    "- Maintain chronological flow with temporal connectors (\"as,\" \"while,\" \"gradually\").\n"
    "- Audio layer: Describe complete soundscape alongside visuals. Be specific "
    "(e.g., \"gentle rain tapping against a frosted window pane\") not vague (e.g., \"rain sounds\").\n"
    "- Camera: Default to STATIC or very slow movement unless otherwise specified.\n"
    "- Style: Include visual style at the beginning: \"Style: <style>, <rest of prompt>.\" Default to cinematic-realistic.\n"
    "- Mood: Emphasize calm, cozy, contemplative, meditative atmospheres.\n"
    "- Visual and audio only: NO non-visual/auditory senses.\n"
    "- Restrained language: Use mild, natural phrasing. Avoid dramatic terms.\n\n"
    "#### Important notes\n"
    "- Camera motion: Default to STATIC. Only add movement if requested.\n"
    "- No timestamps or cuts: Single continuous scene.\n"
    "- Format: Start directly with Style and scene description. NO \"The scene opens with...\"\n"
    "- DO NOT start your response with special characters.\n\n"
    "#### Output Format (Strict):\n"
    "- Single continuous paragraph in natural English.\n"
    "- NO titles, headings, prefaces, code fences, or Markdown.\n"
)

I2V_ENHANCER_SYSTEM = (
    "You are a Creative Assistant specializing in ASMR and ambient video content. "
    "Given an image (first frame) and a user's raw input prompt, generate a prompt to "
    "guide video generation from that image.\n\n"
    "#### Guidelines\n"
    "- Analyze the Image: Identify setting, elements, lighting, mood, and atmosphere.\n"
    "- Follow user prompt: Include all requested motion, audio, and details.\n"
    "- Describe only changes from the image: Don't reiterate established visual details.\n"
    "- Emphasize ambient audio: rain, wind, fire crackle, water flow, rustling, etc.\n"
    "- Active language: present-progressive verbs (\"is falling,\" \"crackling softly\").\n"
    "- Audio layer: Rich soundscape descriptions throughout. Be specific.\n"
    "- Camera: Default to STATIC or very slow movement.\n"
    "- Style: Include visual style at beginning if clear from image. Omit if unclear.\n"
    "- Mood: Calm, cozy, contemplative, meditative atmospheres.\n"
    "- Visual and audio only: Only what is seen and heard.\n\n"
    "#### Important notes\n"
    "- Camera motion: Default to STATIC unless requested.\n"
    "- No timestamps or cuts: Single continuous scene.\n"
    "- Format: Start directly with scene description.\n\n"
    "#### Output Format (Strict):\n"
    "- Single concise paragraph in natural English.\n"
    "- NO titles, headings, prefaces, sections, code fences, or Markdown.\n"
)

DEFAULT_ASMR_PROMPT = (
    "A cozy window scene on a rainy evening. Raindrops gently streak down "
    "a frosted glass window pane. Beyond the glass, blurred city lights glow "
    "warmly in soft orange and yellow bokeh. Inside, a lit candle flickers "
    "softly on the windowsill beside a steaming cup of tea. The sound of "
    "steady rain pattering against the window fills the space, accompanied "
    "by the occasional distant rumble of thunder. The camera remains static, "
    "framing the intimate scene in a medium close-up."
)

DEFAULT_I2V_PROMPT = (
    "Gentle rain begins to fall, droplets sliding slowly down the glass. "
    "The candle flame flickers softly, casting warm dancing shadows. "
    "A steady patter of rain against the window, with distant rumbles of thunder."
)


class WorkflowBuilder:
    """Helper to build ComfyUI workflow JSONs with consistent links."""

    def __init__(self, title="", description=""):
        self.nodes = {}  # id -> node dict
        self.links = []
        self._link_counter = 0
        self._node_order = 0
        self.title = title
        self.description = description

    def add_node(self, node_id, node_type, pos, widgets_values=None, title=None,
                 inputs=None, outputs=None, mode=0, size=None, properties=None):
        """Add a node to the workflow."""
        node = {
            "id": node_id,
            "type": node_type,
            "pos": pos,
            "size": size or [315, 100],
            "flags": {},
            "order": self._node_order,
            "mode": mode,
            "inputs": inputs or [],
            "outputs": outputs or [],
            "properties": properties or {"Node name for S&R": node_type},
        }
        if widgets_values is not None:
            node["widgets_values"] = widgets_values
        if title:
            node["title"] = title
        self._node_order += 1
        self.nodes[node_id] = node
        return node

    def connect(self, src_id, src_slot, dst_id, dst_slot, dtype):
        """Create a link between two nodes."""
        self._link_counter += 1
        link_id = self._link_counter
        self.links.append([link_id, src_id, src_slot, dst_id, dst_slot, dtype])

        # Update source node output links
        src = self.nodes[src_id]
        if src_slot < len(src["outputs"]):
            if "links" not in src["outputs"][src_slot]:
                src["outputs"][src_slot]["links"] = []
            src["outputs"][src_slot]["links"].append(link_id)

        # Update dest node input link
        dst = self.nodes[dst_id]
        if dst_slot < len(dst["inputs"]):
            dst["inputs"][dst_slot]["link"] = link_id

        return link_id

    def build(self):
        """Export as ComfyUI-compatible dict."""
        max_node_id = max(self.nodes.keys()) if self.nodes else 0
        return {
            "id": str(uuid.uuid4()),
            "revision": 0,
            "last_node_id": max_node_id,
            "last_link_id": self._link_counter,
            "nodes": list(self.nodes.values()),
            "links": self.links,
            "groups": [{
                "id": 1,
                "title": self.title,
                "bounding": [-3400, -200, 4200, 1200],
                "color": "#3f789e",
                "font_size": 24,
                "flags": {}
            }],
            "config": {},
            "extra": {
                "ds": {"scale": 0.7, "offset": [800, 200]},
                "info": {"name": self.title, "description": self.description}
            },
            "version": 0.4,
        }


# ---------------------------------------------------------------------------
# Shared node definitions used by both T2V and I2V workflows
# ---------------------------------------------------------------------------

def _output(name, dtype):
    """Shorthand for a single output slot with an empty links list."""
    return [{"name": name, "type": dtype, "links": []}]


def _add_loader_nodes(wb):
    """Add the four loader nodes shared by both workflows (IDs 1-4)."""
    wb.add_node(1, "CheckpointLoaderSimple", [-3200, 0],
        widgets_values=["ltx-2-19b-distilled.safetensors"],
        size=[400, 100],
        outputs=[
            {"name": "MODEL", "type": "MODEL", "links": []},
            {"name": "CLIP", "type": "CLIP", "links": []},
            {"name": "VAE", "type": "VAE", "links": []}
        ])

    wb.add_node(2, "LTXVAudioVAELoader", [-3200, 450],
        widgets_values=["ltx-2-19b-distilled.safetensors"],
        size=[400, 58],
        outputs=_output("Audio VAE", "VAE"))

    wb.add_node(3, "LTXVGemmaCLIPModelLoader", [-3200, 200],
        widgets_values=[
            "gemma-3-12b-it-qat-q4_0-unquantized/model-00001-of-00005.safetensors",
            "ltx-2-19b-distilled.safetensors", 1024
        ],
        size=[400, 100],
        outputs=_output("CLIP", "CLIP"))

    wb.add_node(4, "LatentUpscaleModelLoader", [-3200, 570],
        widgets_values=["ltx-2-spatial-upscaler-x2-1.0.safetensors"],
        size=[400, 58],
        outputs=_output("LATENT_UPSCALE_MODEL", "LATENT_UPSCALE_MODEL"))


def _add_lora_nodes(wb):
    """Add the LoRA chain nodes shared by both workflows (IDs 5-6)."""
    wb.add_node(5, "LoraLoaderModelOnly", [-2700, 0],
        title="Camera LoRA (Static - ASMR)",
        widgets_values=["ltx-2-19b-lora-camera-control-static.safetensors", 1],
        size=[350, 82],
        inputs=[{"name": "model", "type": "MODEL", "link": None}],
        outputs=_output("MODEL", "MODEL"))

    wb.add_node(6, "LoraLoaderModelOnly", [-2700, 150],
        title="Optional Style LoRA (Ctrl+B to enable)",
        widgets_values=["your_camera_lora.safetensors", 1],
        mode=4,  # bypassed
        size=[350, 82],
        inputs=[{"name": "model", "type": "MODEL", "link": None}],
        outputs=_output("MODEL", "MODEL"))


def _add_prompt_nodes(wb, prompt_y, enhancer_system, default_prompt):
    """Add prompt input, enhancer, CLIP encode, and conditioning (IDs 10-13)."""
    wb.add_node(10, "PrimitiveStringMultiline", [-2700, prompt_y],
        title="Your ASMR Prompt",
        widgets_values=[default_prompt],
        size=[450, 180],
        outputs=_output("STRING", "STRING"))

    wb.add_node(11, "LTXVGemmaEnhancePrompt", [-2150, prompt_y - 150],
        title="ASMR Prompt Enhancer",
        widgets_values=["", enhancer_system, 512, True, 42, "randomize"],
        size=[400, 250],
        inputs=[
            {"name": "clip", "type": "CLIP", "link": None},
            {"name": "image", "type": "IMAGE", "link": None, "shape": 7},
            {"name": "prompt", "type": "STRING", "link": None}
        ],
        outputs=_output("STRING", "STRING"))

    wb.add_node(12, "CLIPTextEncode", [-1650, prompt_y - 150],
        title="Enhanced Prompt (Positive)",
        widgets_values=[""],
        size=[300, 100],
        inputs=[
            {"name": "clip", "type": "CLIP", "link": None},
            {"name": "text", "type": "STRING", "widget": {"name": "text"}, "link": None}
        ],
        outputs=_output("CONDITIONING", "CONDITIONING"))

    wb.add_node(13, "LTXVConditioning", [-1250, prompt_y - 150],
        widgets_values=[25],
        size=[210, 94],
        inputs=[
            {"name": "positive", "type": "CONDITIONING", "link": None},
            {"name": "negative", "type": "CONDITIONING", "link": None},
            {"name": "frame_rate", "type": "FLOAT", "widget": {"name": "frame_rate"}, "link": None}
        ],
        outputs=[
            {"name": "positive", "type": "CONDITIONING", "links": []},
            {"name": "negative", "type": "CONDITIONING", "links": []}
        ])


def _add_settings_nodes(wb, settings_y):
    """Add resolution, frame count, and frame rate nodes (IDs 20-23)."""
    wb.add_node(20, "EmptyImage", [-2700, settings_y],
        widgets_values=[768, 512, 1, 0],
        size=[210, 130],
        outputs=_output("IMAGE", "IMAGE"))

    wb.add_node(21, "PrimitiveInt", [-2700, settings_y + 180],
        title="Frame Count (8n+1: 65=2.7s, 97=4s, 121=5s)",
        widgets_values=[65, "fixed"],
        size=[300, 82],
        outputs=_output("INT", "INT"))

    wb.add_node(22, "PrimitiveFloat", [-2700, settings_y + 310],
        title="Frame Rate",
        widgets_values=[24],
        size=[210, 58],
        outputs=_output("FLOAT", "FLOAT"))

    wb.add_node(23, "CM_FloatToInt", [-2400, settings_y + 310],
        title="Frame Rate -> Int",
        widgets_values=[0],
        size=[210, 58],
        inputs=[{"name": "a", "type": "FLOAT", "widget": {"name": "a"}, "link": None}],
        outputs=_output("INT", "INT"))


def _add_output_nodes(wb, output_x, save_prefix):
    """Add CreateVideo and SaveVideo nodes (IDs 40-41)."""
    wb.add_node(40, "CreateVideo", [output_x, 0],
        widgets_values=[30],
        size=[210, 78],
        inputs=[
            {"name": "images", "type": "IMAGE", "link": None},
            {"name": "audio", "type": "AUDIO", "link": None, "shape": 7},
            {"name": "fps", "type": "FLOAT", "widget": {"name": "fps"}, "link": None}
        ],
        outputs=_output("VIDEO", "VIDEO"))

    wb.add_node(41, "SaveVideo", [output_x + 300, 0],
        widgets_values=[save_prefix, "auto", "auto"],
        size=[630, 800],
        inputs=[{"name": "video", "type": "VIDEO", "link": None}],
        outputs=[])


def _wire_shared(wb):
    """Wire connections shared by both T2V and I2V workflows."""
    # Checkpoint -> LoRA 1 -> LoRA 2 -> Sampler stage 1
    wb.connect(1, 0, 5, 0, "MODEL")
    wb.connect(5, 0, 6, 0, "MODEL")
    wb.connect(6, 0, 30, 0, "MODEL")

    # Checkpoint -> Sampler stage 2
    wb.connect(1, 0, 30, 1, "MODEL")

    # Upscale model -> Sampler
    wb.connect(4, 0, 30, 2, "LATENT_UPSCALE_MODEL")

    # Gemma CLIP -> Enhancer + CLIPTextEncode
    wb.connect(3, 0, 11, 0, "CLIP")
    wb.connect(3, 0, 12, 0, "CLIP")

    # Prompt -> Enhancer -> CLIPTextEncode
    wb.connect(10, 0, 11, 2, "STRING")
    wb.connect(11, 0, 12, 1, "STRING")

    # CLIPTextEncode -> LTXVConditioning (positive + negative)
    wb.connect(12, 0, 13, 0, "CONDITIONING")
    wb.connect(12, 0, 13, 1, "CONDITIONING")

    # Frame rate -> LTXVConditioning
    wb.connect(22, 0, 13, 2, "FLOAT")

    # LTXVConditioning -> Sampler
    wb.connect(13, 0, 30, 3, "CONDITIONING")
    wb.connect(13, 1, 30, 4, "CONDITIONING")

    # Frame rate -> int -> Sampler (slot varies, handled by caller)
    wb.connect(22, 0, 23, 0, "FLOAT")

    # Sampler -> CreateVideo -> SaveVideo
    wb.connect(30, 0, 40, 0, "IMAGE")
    wb.connect(30, 1, 40, 1, "AUDIO")
    wb.connect(22, 0, 40, 2, "FLOAT")
    wb.connect(40, 0, 41, 0, "VIDEO")


def build_t2v():
    """Text-to-Video ASMR workflow (distilled model)."""
    wb = WorkflowBuilder(
        "ASMR Text-to-Video (LTX-2 Distilled)",
        "Generate ASMR/ambient video clips from text prompts with built-in audio."
    )

    _add_loader_nodes(wb)
    _add_lora_nodes(wb)
    _add_prompt_nodes(wb, prompt_y=350, enhancer_system=T2V_ENHANCER_SYSTEM,
                      default_prompt=DEFAULT_ASMR_PROMPT)
    _add_settings_nodes(wb, settings_y=620)

    # --- T2V Sampler ---
    wb.add_node(30, T2V_SAMPLER_UUID, [-850, 0],
        widgets_values=[65, 25, 42],
        size=[250, 300],
        properties={},
        inputs=[
            {"label": "model stage 1", "name": "model", "type": "MODEL", "link": None},
            {"label": "model stage 2", "name": "model_1", "type": "MODEL", "link": None},
            {"label": "upscale model", "name": "upscale_model_1", "type": "LATENT_UPSCALE_MODEL", "link": None},
            {"name": "positive", "type": "CONDITIONING", "link": None},
            {"name": "negative", "type": "CONDITIONING", "link": None},
            {"label": "VAE", "name": "vae", "type": "VAE", "link": None},
            {"label": "audio vae", "name": "audio_vae", "type": "VAE", "link": None},
            {"label": "empty latent image", "name": "empty_latent_image", "type": "IMAGE", "link": None},
            {"name": "length", "type": "INT", "widget": {"name": "length"}, "link": None},
            {"label": "frame rate", "name": "frame_rate", "type": "INT", "widget": {"name": "frame_rate"}, "link": None}
        ],
        outputs=[
            {"label": "images", "name": "images", "type": "IMAGE", "links": []},
            {"label": "audio", "name": "audio", "type": "AUDIO", "links": []}
        ])

    _add_output_nodes(wb, output_x=-450, save_prefix="video/ASMR-LTX2")

    # --- Notes ---
    wb.add_node(50, "MarkdownNote", [-3200, -150],
        title="ASMR Text-to-Video",
        size=[600, 130],
        widgets_values=[
            "# ASMR Text-to-Video\n\n"
            "1. Edit **Your ASMR Prompt** with your scene description\n"
            "2. Include audio cues: rain, fire, wind, water, etc.\n"
            "3. Frame Count: 65 = ~2.7s, 97 = ~4s, 121 = ~5s at 24fps\n"
            "4. Width/Height must be divisible by 64\n"
            "5. Click **Queue Prompt** to generate!"
        ],
        inputs=[], outputs=[])

    wb.add_node(51, "MarkdownNote", [-3200, 680],
        title="Video Size Notes",
        size=[400, 80],
        widgets_values=[
            "Width & height must be divisible by **64**.\n"
            "Frame count must follow **8n+1** (9, 17, 25, 33, 41, 49, 57, 65, 73, 81, 89, 97, 105, 113, 121).\n"
            "768x512 base -> upscales to 1536x1024 via spatial upscaler."
        ],
        inputs=[], outputs=[])

    # --- Wiring ---
    _wire_shared(wb)

    # T2V-specific connections
    wb.connect(1, 2, 30, 5, "VAE")        # VAE -> Sampler
    wb.connect(2, 0, 30, 6, "VAE")        # Audio VAE -> Sampler
    wb.connect(20, 0, 30, 7, "IMAGE")     # EmptyImage -> Sampler
    wb.connect(21, 0, 30, 8, "INT")       # Frame count -> Sampler
    wb.connect(23, 0, 30, 9, "INT")       # Frame rate (int) -> Sampler

    return wb.build()


def build_i2v():
    """Image-to-Video ASMR workflow (distilled model)."""
    wb = WorkflowBuilder(
        "ASMR Image-to-Video (LTX-2 Distilled)",
        "Animate a still image into an ASMR video clip with built-in audio."
    )

    _add_loader_nodes(wb)
    _add_lora_nodes(wb)

    # --- Image Input (I2V-specific) ---
    wb.add_node(7, "LoadImage", [-2700, 350],
        title="Load Your Image (from NanoBanana etc.)",
        widgets_values=["example.png", "image"],
        size=[350, 350],
        inputs=[],
        outputs=[
            {"name": "IMAGE", "type": "IMAGE", "links": []},
            {"name": "MASK", "type": "MASK", "links": []}
        ])

    _add_prompt_nodes(wb, prompt_y=750, enhancer_system=I2V_ENHANCER_SYSTEM,
                      default_prompt=DEFAULT_I2V_PROMPT)

    # Override I2V-specific prompt node titles
    wb.nodes[10]["title"] = "Your ASMR Prompt (describe motion + audio only)"
    wb.nodes[10]["size"] = [450, 150]
    wb.nodes[11]["title"] = "ASMR Prompt Enhancer (I2V)"
    # I2V enhancer does not use T2V mode
    wb.nodes[11]["widgets_values"][3] = False

    _add_settings_nodes(wb, settings_y=700)
    # Override I2V settings positions (shifted right for layout)
    for nid in (20, 21, 22):
        wb.nodes[nid]["pos"][0] = -1100
    wb.nodes[23]["pos"][0] = -800

    # --- I2V Sampler ---
    wb.add_node(30, I2V_SAMPLER_UUID, [-450, 0],
        widgets_values=[65, 25, 0.7, 42],
        size=[250, 340],
        properties={},
        inputs=[
            {"label": "model stage 1", "name": "model_1", "type": "MODEL", "link": None},
            {"label": "model stage 2", "name": "model", "type": "MODEL", "link": None},
            {"label": "upscale model", "name": "upscale_model_1", "type": "LATENT_UPSCALE_MODEL", "link": None},
            {"name": "positive", "type": "CONDITIONING", "link": None},
            {"name": "negative", "type": "CONDITIONING", "link": None},
            {"label": "images", "name": "images", "type": "IMAGE", "link": None},
            {"name": "vae", "type": "VAE", "link": None},
            {"label": "audio vae", "name": "audio_vae", "type": "VAE", "link": None},
            {"label": "empty latent image", "name": "image_1", "type": "IMAGE", "link": None},
            {"name": "length", "type": "INT", "widget": {"name": "length"}, "link": None},
            {"label": "frame rate", "name": "frame_rate", "type": "INT", "widget": {"name": "frame_rate"}, "link": None},
            {"label": "image strength", "name": "strength", "type": "FLOAT", "widget": {"name": "strength"}, "link": None}
        ],
        outputs=[
            {"label": "images", "name": "images", "type": "IMAGE", "links": []},
            {"label": "audio", "name": "audio", "type": "AUDIO", "links": []}
        ])

    _add_output_nodes(wb, output_x=-50, save_prefix="video/ASMR-LTX2-I2V")

    # --- Notes ---
    wb.add_node(50, "MarkdownNote", [-3200, -150],
        title="ASMR Image-to-Video",
        size=[600, 130],
        widgets_values=[
            "# ASMR Image-to-Video\n\n"
            "1. Upload your image in the **Load Image** node\n"
            "2. Describe the **motion and audio** -- don't repeat what's already in the image\n"
            "3. Image Strength: 0.7 = balanced, 0.9 = very faithful to image\n"
            "4. Enhancer adds audio detail automatically\n"
            "5. Click **Queue Prompt** to generate!"
        ],
        inputs=[], outputs=[])

    # --- Wiring ---
    _wire_shared(wb)

    # I2V-specific connections
    wb.connect(7, 0, 11, 1, "IMAGE")      # Image -> Enhancer (visual context)
    wb.connect(7, 0, 30, 5, "IMAGE")      # Image -> Sampler (conditioning)
    wb.connect(1, 2, 30, 6, "VAE")        # VAE -> Sampler
    wb.connect(2, 0, 30, 7, "VAE")        # Audio VAE -> Sampler
    wb.connect(20, 0, 30, 8, "IMAGE")     # EmptyImage -> Sampler
    wb.connect(21, 0, 30, 9, "INT")       # Frame count -> Sampler
    wb.connect(23, 0, 30, 10, "INT")      # Frame rate (int) -> Sampler

    return wb.build()


def save_workflow(wf, filename):
    """Save workflow JSON."""
    path = WORKFLOWS_DIR / filename
    with open(path, "w") as f:
        json.dump(wf, f, indent=2)
    print(f"  Saved: {path}")


if __name__ == "__main__":
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating ASMR workflows...")

    save_workflow(build_t2v(), "asmr-txt2vid.json")
    save_workflow(build_i2v(), "asmr-img2vid.json")

    print("\nDone! Generated 2 core workflow files.")
    print("\nNote: The extend, upscale, and full-pipeline workflows are best")
    print("created by loading the official examples in ComfyUI and adapting.")
    print("See README.md for instructions.")
