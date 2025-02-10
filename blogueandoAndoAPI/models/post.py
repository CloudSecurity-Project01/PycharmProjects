from pydantic import BaseModel, ConfigDict
from typing import Optional
from blogueandoAndoAPI.models.tag import Tag


class PostIn(BaseModel):
    title: str
    content: str
    user_id: int


class Post(PostIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    publication_date: str
    public: bool
    rating: Optional[int]
    tags: Optional[list[str]]


class MyPostIn(BaseModel):
    user_id: int


class PostRating(BaseModel):
    user_id: int
    post_id: int
    rating: int


class PostTag(BaseModel):
    post_id: int
    tag_id: int


