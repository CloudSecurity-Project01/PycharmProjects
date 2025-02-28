from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from typing import Dict, Any, Optional
import sqlalchemy as sa

from blogueandoAndoAPI.models.tag import TagIn, Tag
from blogueandoAndoAPI.helpers.database import Post as post_table
from blogueandoAndoAPI.helpers.database import Tag as tag_table
from blogueandoAndoAPI.helpers.database import Post_Tag as post_tag_table
from blogueandoAndoAPI.helpers.database import fetch_all, insert, delete, fetch_one, fetch_all_query
from blogueandoAndoAPI.helpers.security import get_current_user_optional
from blogueandoAndoAPI.helpers.pagination import paginate_query

router = APIRouter()

@router.get("/tags", response_model=Dict[str, Any])
async def all_tags(size: int, skip: int, filter: str = "all", current_user: Optional[dict] = Depends(get_current_user_optional)):
    if filter == "mine":
        if current_user is None:
            raise HTTPException(status_code=401, detail="No estás autorizado para realizar esta acción")

        available_post_ids_query = select(post_table.id).where(post_table.user_id == current_user["id"])

    else:
        available_post_ids_query = select(post_table.id).where(
            sa.or_(
                post_table.is_public == True,
                ((current_user is not None) and (post_table.user_id == current_user["id"]))
            )
        )

    available_post_ids = fetch_all_query(available_post_ids_query)

    if not available_post_ids:
        return {"tags": [], "current_page": 0, "total_pages": 0, "total_items": 0}

    post_ids = [post["id"] for post in available_post_ids]

    tags_query = (
        select(tag_table)
        .join(post_tag_table, post_tag_table.tag_id == tag_table.id)
        .where(post_tag_table.post_id.in_(post_ids))
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
    tags = fetch_all(
        tag_table, True)
    filtered_tags = []
    for t in tags:
        if tag.tag.lower() in t["tag"].lower():
            filtered_tags.append(t)
    return filtered_tags


@router.post("/create_tag", response_model=Tag)
async def create_tag(tag: TagIn):
    data = tag.dict()
    new_tag = insert(
        tag_table,
        data
    )
    last_record_id = new_tag.lastrowid
    return {**data, "id": last_record_id}

def get_tags(post_id):
    try:
        validate_post_existence(post_id)
    except Exception as exception:
        raise exception

    post_tags = fetch_all(
        post_tag_table,
        post_tag_table.post_id == post_id
    )
    tagIds = []
    for i in post_tags:
        tagIds.append(i["tag_id"])

    return fetch_all(
        tag_table,
        tag_table.id.in_(tagIds)
    )


def validate_post_existence(post_id: int):
    post = fetch_one(
        post_table,
        post_table.id == post_id
    )
    if post is None:
        raise HTTPException(status_code=404, detail="No se encontró la publicación")

def assign_tags_to_post(post_id: int, tags: list[str]):
    existing_tags = fetch_all(
        post_tag_table,
        post_tag_table.post_id == post_id
    )
    existing_tag_ids = {tag["tag_id"] for tag in existing_tags}

    tag_ids = []
    for tag_name in tags:
        existing_tag = fetch_one(
            tag_table,
            tag_table.tag == tag_name
        )

        if existing_tag:
            tag_id = existing_tag["id"]
        else:
            new_tag = insert(tag_table, {"tag": tag_name})
            tag_id = new_tag.lastrowid

        tag_ids.append(tag_id)

    tags_to_remove = existing_tag_ids - set(tag_ids)
    if tags_to_remove:
        delete(
            post_tag_table,
            (post_tag_table.post_id == post_id) & (post_tag_table.tag_id.in_(tags_to_remove))
        )

    for tag_id in tag_ids:
        if tag_id not in existing_tag_ids:
            insert(
                post_tag_table,
                {"post_id": post_id, "tag_id": tag_id}
            )


