from fastapi import APIRouter, HTTPException
from blogueandoAndoAPI.models.tag import TagIn, Tag
from blogueandoAndoAPI.models.post import Pagination
from blogueandoAndoAPI.helpers.database import tag_table, database, post_tag_table, post_table

router = APIRouter()

@router.get("/tags", response_model=list[Tag])
async def all_tag(pagination: Pagination):
    query = tag_table.select().offset(pagination.skip).limit(pagination.size)
    return await database.fetch_all(query)


@router.get("/filter_tag", response_model=list[Tag])
async def find_tags(tag: TagIn):
    query = tag_table.select()
    tags = await database.fetch_all(query)
    filtered_tags = []
    for t in tags:
        if tag.tag.lower() in t["tag"].lower():
            filtered_tags.append(t)
    return filtered_tags


async def get_tags(post_id):
    try:
        await validate_post_existence(post_id)
    except Exception as exception:
        raise exception

    query = post_tag_table.select().where(post_tag_table.c.post_id == post_id)
    post_tags = await database.fetch_all(query)
    tagIds = []
    for i in post_tags:
        tagIds.append(i["tag_id"])

    query = tag_table.select().where(tag_table.c.id.in_(tagIds))
    return await database.fetch_all(query)


async def validate_post_existence(post_id: int):
    query = post_table.select().where(post_table.c.id == post_id)
    post = await database.fetch_one(query)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
