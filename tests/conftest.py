import pytest

from app.models.output import GeneratedAsset
from app.models.product import Category, ProductRow


@pytest.fixture
def sample_product_row() -> ProductRow:
    """A valid ProductRow fixture for use across all test modules."""
    return ProductRow(
        id="001",
        name="Weekend Spa Escape",
        location="Wicklow Mountains",
        price=149.0,
        category=Category.wellness,
        key_selling_point="Two-night stay with full-day spa access in a mountain retreat",
    )


@pytest.fixture
def sample_product_rows() -> list[ProductRow]:
    """A list of five ProductRow fixtures covering all categories."""
    return [
        ProductRow(
            id="001",
            name="Weekend Spa Escape",
            location="Wicklow Mountains",
            price=149.0,
            category=Category.wellness,
            key_selling_point="Two-night stay with full-day spa access in a mountain retreat",
        ),
        ProductRow(
            id="002",
            name="Helicopter Tour of Dublin Bay",
            location="Dublin",
            price=199.0,
            category=Category.adventure,
            key_selling_point="30-minute aerial tour over the coastline for two people",
        ),
        ProductRow(
            id="003",
            name="Michelin-Starred Tasting Menu",
            location="Cork City",
            price=129.0,
            category=Category.gastronomy,
            key_selling_point="Seven-course dinner at a celebrated Irish restaurant",
        ),
        ProductRow(
            id="004",
            name="Coastal Kayaking Adventure",
            location="Wild Atlantic Way",
            price=79.0,
            category=Category.adventure,
            key_selling_point="Half-day guided sea kayaking along Ireland's dramatic west coast",
        ),
        ProductRow(
            id="005",
            name="Castle Getaway for Two",
            location="County Clare",
            price=219.0,
            category=Category.getaways,
            key_selling_point="Two-night stay in a 15th century restored Irish castle",
        ),
    ]


@pytest.fixture
def mock_llm_response(sample_product_row: ProductRow) -> GeneratedAsset:
    """A fully populated GeneratedAsset fixture simulating LLM output."""
    return GeneratedAsset(
        product_id=sample_product_row.id,
        video_script=(
            "Picture this: misty mountains, a warm pool, and two whole days to forget "
            "the world exists. The Wicklow Mountains are calling. Your spa escape starts now."
        ),
        voiceover_copy=(
            "Slip away to the Wicklow Mountains for a weekend that's all about you. "
            "Full spa access, mountain air, and the kind of quiet you actually need."
        ),
        image_prompt=(
            "Aerial view of a luxury mountain spa at golden hour, warm amber light "
            "filtering through pine trees onto an outdoor thermal pool, misty hills "
            "in the background, cinematic wide-angle photography, rich earthy tones."
        ),
        video_prompt=(
            "Slow aerial drone gliding over misty mountain spa at sunrise, "
            "steam rising from outdoor thermal pool, golden light through pine trees, "
            "cinematic wide angle."
        ),
        hashtags=["spaWeekend", "wicklowMountains", "selfCare", "irishGetaway", "wellnessTravel"],
        dam_filename="PROD-001_WELLNESS_IE_20240101.mp4",
        image_url="https://image.pollinations.ai/prompt/spa%20mountains?model=flux",
        video_url="",
        image_status="done",
        video_status="skipped",
    )


@pytest.fixture
def mock_image_response() -> tuple[str, str]:
    """Mock return value from image_service.generate_image()."""
    return (
        "https://image.pollinations.ai/prompt/test?model=flux",
        "done",
    )


@pytest.fixture
def mock_video_response() -> tuple[str, str]:
    """Mock return value from video_service.generate_video() when skipped."""
    return ("", "skipped")
