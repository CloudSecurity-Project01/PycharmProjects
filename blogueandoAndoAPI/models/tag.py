from pydantic import BaseModel, ConfigDict


class TagIn(BaseModel):
    tag: str


class Tag(TagIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


