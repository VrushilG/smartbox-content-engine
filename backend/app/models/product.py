from enum import Enum

from pydantic import BaseModel, ConfigDict


class Category(str, Enum):
    getaways = "getaways"
    wellness = "wellness"
    adventure = "adventure"
    gastronomy = "gastronomy"
    pampering = "pampering"


class ProductRow(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    name: str
    location: str
    price: float
    category: Category
    key_selling_point: str
