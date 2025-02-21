from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from typing import Dict, Any, Optional
import sqlalchemy as sa

from blogueandoAndoAPI.models.tag import TagIn, Tag
from blogueandoAndoAPI.helpers.database import tag_table, database, post_tag_table, post_table
from blogueandoAndoAPI.helpers.security import get_current_user_optional
from blogueandoAndoAPI.helpers.pagination import paginate_query

router = APIRouter()

@router.get("/tags", response_model=Dict[str, Any])
async def all_tags(size: int, skip: int, filter: str = "all", current_user: Optional[dict] = Depends(get_current_user_optional)):
    if filter == "mine":
        if current_user is None:
            raise HTTPException(status_code=401, detail="No estás autorizado para realizar esta acción")
        
        available_post_ids_query = select(post_table.c.id).where(post_table.c.user_id == current_user["id"])
    else:
        available_post_ids_query = select(post_table.c.id).where(
            sa.or_(
                post_table.c.is_public == True,
                ((current_user is not None) and (post_table.c.user_id == current_user["id"]))
            )
        )

    available_post_ids = await database.fetch_all(available_post_ids_query)

    if not available_post_ids:
        return {"tags": [], "current_page": 0, "total_pages": 0, "total_items": 0}

    post_ids = [post["id"] for post in available_post_ids]

    tags_query = (
        select(tag_table)
        .join(post_tag_table, post_tag_table.c.tag_id == tag_table.c.id)
        .where(post_tag_table.c.post_id.in_(post_ids))
    ).distinct()
       
    tags, current_page, total_pages, total_items = await paginate_query(tags_query, size, skip)

    return {
        "tags": [tag["tag"] for tag in tags],
        "current_page": current_page,
        "total_pages": total_pages,
        "total_items": total_items
    }


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

