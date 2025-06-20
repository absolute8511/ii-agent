# src/ii_agent/tools/image_generate_tool.py

import os
from pathlib import Path
from typing import Any, Optional
from io import BytesIO

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

try:
    import vertexai
    from vertexai.preview.vision_models import (
        ImageGenerationModel,
    )  # Use preview for Imagen 3
    HAS_VERTEX = True
except ImportError:
    HAS_VERTEX = False

from PIL import Image

from ii_agent.tools.base import (
    MessageHistory,
    LLMTool,
    ToolImplOutput,
)
from ii_agent.utils import WorkspaceManager

MEDIA_GCP_PROJECT_ID = os.environ.get("MEDIA_GCP_PROJECT_ID")
MEDIA_GCP_LOCATION = os.environ.get("MEDIA_GCP_LOCATION")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

SUPPORTED_ASPECT_RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4"]
SAFETY_FILTER_LEVELS = ["block_some", "block_most", "block_few"]
PERSON_GENERATION_OPTIONS = ["allow_adult", "dont_allow", "allow_all"]

# Google AI Studio person generation mapping
GENAI_PERSON_GENERATION_MAP = {
    "allow_adult": "ALLOW_ADULT",
    "dont_allow": "DONT_ALLOW",
    "allow_all": "ALLOW_ALL"
}


class ImageGenerateTool(LLMTool):
    name = "generate_image_from_text"
    description = """Generates an image based on a text prompt using Google's Imagen 3 model via Vertex AI or Google AI Studio.
The generated image will be saved to the specified local path in the workspace as a PNG file."""
    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "A detailed description of the image to be generated.",
            },
            "output_filename": {
                "type": "string",
                "description": "The desired relative path for the output PNG image file within the workspace (e.g., 'generated_images/my_image.png'). Must end with .png.",
            },
            "number_of_images": {
                "type": "integer",
                "default": 1,
                "description": "Number of images to generate (currently, the example shows 1, stick to 1 unless API supports more easily).",
            },
            "aspect_ratio": {
                "type": "string",
                "enum": SUPPORTED_ASPECT_RATIOS,
                "default": "1:1",
                "description": "The aspect ratio for the generated image.",
            },
            "seed": {
                "type": "integer",
                "description": "(Optional) A seed for deterministic generation. If provided, add_watermark will be forced to False as they are mutually exclusive.",
            },
            "add_watermark": {
                "type": "boolean",
                "default": True,  # Defaulting to True as per general Vertex AI Imagen behavior
                "description": "Whether to add a watermark to the generated image. Cannot be used with 'seed'.",
            },
            "safety_filter_level": {
                "type": "string",
                "enum": SAFETY_FILTER_LEVELS,
                "default": "block_some",
                "description": "The safety filter level to apply.",
            },
            "person_generation": {
                "type": "string",
                "enum": PERSON_GENERATION_OPTIONS,
                "default": "allow_adult",
                "description": "Controls the generation of people.",
            },
        },
        "required": ["prompt", "output_filename"],
    }

    def __init__(self, workspace_manager: WorkspaceManager):
        super().__init__()
        self.workspace_manager = workspace_manager
        self.api_type = None
        self.model = None
        self.genai_client = None

        # Prefer Google AI Studio if GEMINI_API_KEY is available
        if GEMINI_API_KEY and HAS_GENAI:
            try:
                self.genai_client = genai.Client(api_key=GEMINI_API_KEY)
                self.api_type = "genai"
                print("Using Google AI Studio for image generation")
            except Exception as e:
                print(f"Error initializing Google AI Studio: {e}")
                self.genai_client = None

        # Fall back to Vertex AI if Google AI Studio is not available
        if not self.api_type and MEDIA_GCP_PROJECT_ID and MEDIA_GCP_LOCATION and HAS_VERTEX:
            try:
                vertexai.init(project=MEDIA_GCP_PROJECT_ID, location=MEDIA_GCP_LOCATION)
                self.model = ImageGenerationModel.from_pretrained(
                    "imagen-3.0-generate-002"
                )
                self.api_type = "vertex"
                print("Using Vertex AI for image generation")
            except Exception as e:
                print(f"Error initializing Vertex AI or loading Imagen model: {e}")
                self.model = None

        if not self.api_type:
            raise ValueError(
                "Neither Google AI Studio (GEMINI_API_KEY) nor Vertex AI (MEDIA_GCP_PROJECT_ID and MEDIA_GCP_LOCATION) are properly configured. "
                "Please set either GEMINI_API_KEY or both MEDIA_GCP_PROJECT_ID and MEDIA_GCP_LOCATION environment variables."
            )

    async def run_impl(
        self,
        tool_input: dict[str, Any],
        message_history: Optional[MessageHistory] = None,
    ) -> ToolImplOutput:
        if not self.api_type:
            return ToolImplOutput(
                "Error: No image generation API is configured. Check your environment variables.",
                "Image generation API not configured.",
                {"success": False, "error": "API not configured"},
            )
        prompt = tool_input["prompt"]
        relative_output_filename = tool_input["output_filename"]

        if not relative_output_filename.lower().endswith(".png"):
            return ToolImplOutput(
                "Error: output_filename must end with .png for Imagen generation.",
                "Invalid output filename for image.",
                {"success": False, "error": "Output filename must be .png"},
            )

        local_output_path = self.workspace_manager.workspace_path(
            Path(relative_output_filename)
        )
        local_output_path.parent.mkdir(parents=True, exist_ok=True)

        generate_params = {
            "number_of_images": tool_input.get("number_of_images", 1),
            "language": "en",  # Explicitly setting, though API might default
            "aspect_ratio": tool_input.get("aspect_ratio", "1:1"),
            "safety_filter_level": tool_input.get("safety_filter_level", "block_some"),
            "person_generation": tool_input.get("person_generation", "allow_adult"),
        }

        seed = tool_input.get("seed")
        add_watermark = tool_input.get("add_watermark", True)

        if seed is not None:
            generate_params["seed"] = int(seed)
            if add_watermark:
                print(
                    "Warning: 'seed' is provided, 'add_watermark' will be ignored (or set to False)."
                )
                generate_params["add_watermark"] = False
        elif "add_watermark" in tool_input:
            generate_params["add_watermark"] = add_watermark

        try:
            if self.api_type == "genai":
                # Use Google AI Studio API
                genai_config = {
                    "number_of_images": tool_input.get("number_of_images", 1),
                    "output_mime_type": "image/jpeg",  # Google AI Studio uses JPEG
                    "aspect_ratio": tool_input.get("aspect_ratio", "1:1"),
                    "person_generation": GENAI_PERSON_GENERATION_MAP.get(
                        tool_input.get("person_generation", "allow_adult"), "ALLOW_ADULT"
                    ),
                }
                
                # Note: Google AI Studio doesn't support seed with watermark like Vertex
                # We'll ignore watermark settings for Google AI Studio
                
                result = self.genai_client.models.generate_images(
                    model="models/imagen-3.0-generate-002",
                    prompt=prompt,
                    config=genai_config,
                )
                
                if not result.generated_images:
                    return ToolImplOutput(
                        f"Image generation failed for prompt: {prompt}. No images returned.",
                        "Image generation produced no output.",
                        {"success": False, "error": "No images returned from API"},
                    )
                
                # Save the first generated image
                generated_image = result.generated_images[0]
                image = Image.open(BytesIO(generated_image.image.image_bytes))
                
                # Convert to PNG as expected by our tool
                image.save(str(local_output_path), "PNG")
                
            else:  # vertex AI
                images = self.model.generate_images(prompt=prompt, **generate_params)

                if not images:  # Response could be None or empty list
                    return ToolImplOutput(
                        f"Image generation failed for prompt: {prompt}. No images returned.",
                        "Image generation produced no output.",
                        {"success": False, "error": "No images returned from API"},
                    )

                if generate_params["number_of_images"] > 1:
                    print(
                        f"Warning: Requested {generate_params['number_of_images']} images, but tool currently saves only the first."
                    )
                try:
                    images[0].save(
                        location=str(local_output_path), include_generation_parameters=False
                    )  # include_generation_parameters=False as per snippet
                except Exception as e:
                    msg = "Image generation failed due to safety restrictions or API limitations. Please try modifying your prompt to be more appropriate or let me know if you'd like to try a different approach."
                    return ToolImplOutput(msg, msg, {"success": False, "error": str(e)})
            output_url = (
                f"http://localhost:{self.workspace_manager.file_server_port}/workspace/{relative_output_filename}"
                if hasattr(self.workspace_manager, "file_server_port")
                else f"(Local path: {relative_output_filename})"
            )

            return ToolImplOutput(
                f"Successfully generated image from text and saved to '{relative_output_filename}'. View at: {output_url}",
                f"Image generated and saved to {relative_output_filename}",
                {
                    "success": True,
                    "output_path": relative_output_filename,
                    "url": output_url,
                },
            )

        except Exception as e:
            return ToolImplOutput(
                f"Error generating image from text: {str(e)}",
                "Failed to generate image from text.",
                {"success": False, "error": str(e)},
            )

    def get_tool_start_message(self, tool_input: dict[str, Any]) -> str:
        return f"Generating image from text prompt, saving to: {tool_input['output_filename']}"
