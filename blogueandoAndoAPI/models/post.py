from pydantic import BaseModel, ConfigDict
from typing import Optional
from blogueandoAndoAPI.models.tag import Tag


class PostIn(BaseModel):
    title: str
    content: str
    user_id: int
    is_public: Optional[bool] = None
    tags: Optional[list[str]] = None

class Post(PostIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    content_location: str
    publication_date: str
    rating: Optional[float]
    user_name: str

class MyPostIn(BaseModel):
    user_id: int

class PostRating(BaseModel):
    post_id: int
    rating: int

class PostTag(BaseModel):
    post_id: int
    tags: list[str]

class Pagination(BaseModel):
    size: int
    skip: int

class PostUpload(BaseModel):
    filename: str
    content: str