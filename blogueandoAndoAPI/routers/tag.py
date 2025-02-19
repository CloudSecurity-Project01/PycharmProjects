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
        raise HTTPException(status_code=404, detail="No se encontró la publicación")

async def assign_tags_to_post(post_id: int, tags: list[str]):
    query = post_tag_table.select().where(post_tag_table.c.post_id == post_id)
    existing_tags = await database.fetch_all(query)
    existing_tag_ids = {tag["tag_id"] for tag in existing_tags}

    tag_ids = []
    for tag_name in tags:
        query = tag_table.select().where(tag_table.c.tag == tag_name)
        existing_tag = await database.fetch_one(query)

        if existing_tag:
            tag_id = existing_tag["id"]
        else:
            query = tag_table.insert().values(tag=tag_name)
            tag_id = await database.execute(query)
        
        tag_ids.append(tag_id)

    tags_to_remove = existing_tag_ids - set(tag_ids)
    if tags_to_remove:
        query = post_tag_table.delete().where(
            (post_tag_table.c.post_id == post_id) & (post_tag_table.c.tag_id.in_(tags_to_remove))
        )
        await database.execute(query)

    for tag_id in tag_ids:
        if tag_id not in existing_tag_ids:
            query = post_tag_table.insert().values(post_id=post_id, tag_id=tag_id)
            await database.execute(query)

