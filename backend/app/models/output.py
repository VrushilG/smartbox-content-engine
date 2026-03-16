from pydantic import BaseModel, ConfigDict


class GeneratedAsset(BaseModel):
    model_config = ConfigDict(strict=True)

    product_id: str
    video_script: str
    voiceover_copy: str
    product_description: str = ""  # 2-3 sentence product description for email/social/website use
    image_prompt: str       # Full visual prompt — fed to image_service
    video_prompt: str       # Short cinematic prompt (20-40 words) — fed to video_service
    hashtags: list[str]
    dam_filename: str       # Set by pipeline after generation

    # Media URLs — set by pipeline after calling image/video services
    image_url: str = ""
    video_url: str = ""

    # Generation status for each media type
    # Values: "skipped" | "generating" | "done" | "failed"
    image_status: str = "skipped"
    video_status: str = "skipped"

    # Human-readable reason for failure (empty when status is not "failed")
    video_error: str = ""
    image_error: str = ""
