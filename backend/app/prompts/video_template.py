SMARTBOX_VIDEO_TEMPLATE = (
    "Drone aerial shot slowly approaching a premium Smartbox gift box placed in "
    "{environment_hint}. The box features Smartbox premium packaging with the company "
    "branding visible on the lid. As the drone reaches the box, the lid opens smoothly "
    "with a soft magical glow. Inside the box: {scene}. "
    "Premium travel-commercial cinematic style, smooth camera motion, natural lighting, "
    "joyful authentic emotions, 4 seconds total."
)


def build_video_prompt(scene: str, environment_hint: str = "a scenic outdoor location") -> str:
    """Compose the full branded Smartbox video prompt from a scene description.

    Args:
        scene: LLM-generated scene description (15–25 words of who/what/where/mood).
        environment_hint: Short phrase describing where the gift box sits, derived
                          from the product location. E.g. "the Cliffs of Moher clifftop".

    Returns:
        The complete video prompt string ready to pass to the video generation service.
    """
    return SMARTBOX_VIDEO_TEMPLATE.format(
        scene=scene.strip(),
        environment_hint=environment_hint.strip(),
    )
