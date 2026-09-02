from pydantic import BaseModel, Field


class Restaurant(BaseModel):
    item_id: int
    name: str
    location: str
    type: str
    food_style: str
    rating: float | None = None
    price_range: int | None = Field(default=None, ge=1, le=4)
    signatures: list[str] = Field(default_factory=list)
    vibe: str | None = None
    environment: str
    shortcomings: list[str] = Field(default_factory=list)
    source_text: str


class Recipe(BaseModel):
    id: int
    name: str
    cuisine: str
    servings: int
    prep_time: str
    cook_time: str
    total_time: str
    ingredients: list[str]
    directions: list[str]
    image_path: str | None = None
    image_description: str | None = None


class Review(BaseModel):
    review_id: int
    user_id: str
    item_id: int
    title: str
    text: str
    date: str
    rating: float
    language: str
    images: list[str] = Field(default_factory=list)
    image_captions: list[str] = Field(default_factory=list)
