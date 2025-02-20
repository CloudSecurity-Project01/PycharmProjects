from fastapi import APIRouter, HTTPException, Query, Depends
from blogueandoAndoAPI.models.post import PostIn, Post, PostRating, PostTag
from blogueandoAndoAPI.models.tag import TagIn
from blogueandoAndoAPI.routers.tag import get_tags, find_tags, validate_post_existence, assign_tags_to_post
from blogueandoAndoAPI.helpers.database import user_table, post_table, rating_table, post_tag_table, database, tag_table
from blogueandoAndoAPI.helpers.security import get_current_user_optional, get_current_user
from blogueandoAndoAPI.helpers.pagination import paginate_query
from fastapi.security import OAuth2PasswordBearer
from typing import Optional, Dict, Any, List
import sqlalchemy as sa
import datetime

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@router.post("/post", response_model=Post, status_code=201)
async def create_post(post: PostIn, current_user: dict = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="No estás autorizado para realizar esta acción")

    async with database.transaction():
        post_dict = post.model_dump()
        tags = post_dict.pop("tags", [])
        data = {
            **post_dict,
            "publication_date": datetime.datetime.now().strftime("%D"),
            "is_public": True,
            "user_id": current_user.id,
        }
        query = post_table.insert().values(data)
        last_record_id = await database.execute(query)

        if tags:
            await assign_tags_to_post(last_record_id, tags)

        query = post_table.select().where(post_table.c.id == last_record_id)
        post_data = await database.fetch_one(query)
        
    return {**await post_with_extra_inf(post_data), "user_name": current_user.user_name}


@router.get("/posts", response_model=Dict[str, Any])
async def get_posts(
    size: int, 
    skip: int, 
    filter: str = "all",  
    tags: Optional[List[str]] = Query(None),
    tag_filter_mode: str = Query("and", regex="^(and|or)$"),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    base_query = sa.select(post_table, user_table.c.name.label("user_name")).join(
        user_table, post_table.c.user_id == user_table.c.id
    )

    if filter == "mine":
        if current_user is None:
            raise HTTPException(status_code=401, detail="No estás autorizado para realizar esta acción")
        user_id = current_user["id"]
        base_query = base_query.where(post_table.c.user_id == user_id)
    else:
        base_query = base_query.where(
            sa.or_(
                post_table.c.is_public == True,
                ((current_user is not None) and (post_table.c.user_id == current_user["id"]))
            )
        )

    if tags:
        tag_subquery = sa.select(post_tag_table.c.post_id).join(
            tag_table, tag_table.c.id == post_tag_table.c.tag_id
        )

        if tag_filter_mode == "and":
            for tag in tags:
                base_query = base_query.where(
                    post_table.c.id.in_(
                        tag_subquery.where(tag_table.c.tag == tag)
                    )
                )
        else:
            base_query = base_query.where(
                post_table.c.id.in_(
                    tag_subquery.where(tag_table.c.tag.in_(tags))
                )
            )

    posts, current_page, total_pages, total_items = await paginate_query(base_query, size, skip)

    return {
        "posts": await posts_with_extra_info(posts),
        "current_page": current_page,
        "total_pages": total_pages,
        "total_items": total_items
    }


@router.get("/posts_ids", response_model=List[int])
async def get_visible_post_ids(filter: str = "all", current_user: Optional[dict] = Depends(get_current_user_optional)):
    base_query = sa.select(post_table.c.id)

    if filter == "mine":
        if not current_user:
            return []
        base_query = base_query.where(post_table.c.user_id == current_user["id"])
    else:
        base_query = base_query.where(
            sa.or_(
                post_table.c.is_public == True,
                ((current_user is not None) and (post_table.c.user_id == current_user["id"]))
            )
        )

    result = await database.fetch_all(base_query)
    post_ids = [row["id"] for row in result]

    return post_ids

@router.get("/post", response_model=Post)
async def get_post(id: int = Query(...), current_user: Optional[dict] = Depends(get_current_user_optional)):
    query = (
        sa.select(post_table, user_table.c.name.label("user_name"))
        .join(user_table, post_table.c.user_id == user_table.c.id)
        .where(post_table.c.id == id)
        .where(
            sa.or_(
                post_table.c.is_public == True,
                ((current_user is not None) and (post_table.c.user_id == current_user["id"]))
            )
        )
    )
    post = await database.fetch_one(query)

    if not post:
        raise HTTPException(status_code=404, detail="No se encontró la publicación")
    
    return await post_with_extra_inf(post)


@router.put("/post/{post_id}", response_model=Post)
async def update_post(post_id: int, post: PostIn, current_user: dict = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="No estás autorizado para realizar esta acción")

    async with database.transaction():
        query = post_table.select().where(post_table.c.id == post_id)
        existing_post = await database.fetch_one(query)

        if existing_post is None:
            raise HTTPException(status_code=404, detail="No se encontró la publicación")

        if existing_post["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="No tienes permiso para editar esta publicación")

        updated_data = {
            "title": post.title,
            "content": post.content,
            "is_public": post.is_public,
        }

        query = post_table.update().where(post_table.c.id == post_id).values(updated_data)
        await database.execute(query)

        if post.tags is not None:
            await assign_tags_to_post(post_id, post.tags)

        rating = await get_rating(post_id)

        updated_post = {
            **updated_data,
            "id": post_id,
            "rating": rating,
            "tags": post.tags if post.tags is not None else [],
            "publication_date": existing_post["publication_date"],
            "user_name": current_user.user_name,
            "user_id": current_user.id,
        }

    return updated_post


@router.delete("/post/{post_id}", status_code=200)
async def delete_post(post_id: int, current_user: dict = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="No estás autorizado para realizar esta acción")

    query = post_table.select().where(post_table.c.id == post_id)
    existing_post = await database.fetch_one(query)
    if existing_post is None:
        raise HTTPException(status_code=404, detail="No se encontró la publicación")
    
    if existing_post["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar esta publicación")

    async with database.transaction():
        query = post_tag_table.select().where(post_tag_table.c.post_id == post_id)
        post_tags = await database.fetch_all(query)

        query = post_tag_table.delete().where(post_tag_table.c.post_id == post_id)
        await database.execute(query)

        for post_tag in post_tags:
            tag_id = post_tag["tag_id"]
            query = sa.select(post_tag_table.c.post_id).where(post_tag_table.c.tag_id == tag_id)
            remaining_posts = await database.fetch_all(query)
            if not remaining_posts:
                query = tag_table.delete().where(tag_table.c.id == tag_id)
                await database.execute(query)

        query = post_table.delete().where(post_table.c.id == post_id)
        await database.execute(query)

    return {"detail": "Publicación eliminada con éxito"}


async def posts_with_extra_info(posts):
    fixed_posts = []
    for post in posts:
        fixed_post = await post_with_extra_inf(post)
        fixed_posts.append(fixed_post)
    return fixed_posts

async def post_with_extra_inf(post):
    rating = await get_rating(post["id"])
    tags = await get_tags(post["id"])
    tag = []
    for t in tags:
        print(t.keys())
        tag.append(t["tag"])
    return {**post, "rating": rating, "tags": tag}


@router.post("/set_rating", response_model=PostRating)
async def post_rating(post: PostRating):
    try:
        await validate_post_existence(post.post_id)
    except Exception as exception:
        raise exception

    async with database.transaction():
        data = post.model_dump()
        if data["rating"] > 5 or data["rating"] < 1:
            raise HTTPException(status_code=406, detail="El valor de la calificación está fuera del rango permitido")
        query = rating_table.insert().values(data)
        await database.execute(query)
    
    return post


@router.post("/set_tags", response_model=Post)
async def add_tags(post: PostTag):
    await validate_post_existence(post.post_id)
    
    async with database.transaction():
        await assign_tags_to_post(post.post_id, post.tags)
        query = post_table.select().where(post_table.c.id == post.post_id)
        post_data = await database.fetch_one(query)
    
    return await post_with_extra_inf(post_data)


@router.get("/get_posts_tag", response_model=list[Post])
async def get_post_with_tags(tag: TagIn):
    tags = await find_tags(tag)
    if len(tags) == 0:
        return []

    tag_ids = []
    for i in tags:
        tag_ids.append(i["id"])

    query = post_tag_table.select().where(post_tag_table.c.tag_id.in_(tag_ids))
    post_tags = await database.fetch_all(query)

    post_ids = []
    for i in post_tags:
        post_ids.append(i["post_id"])

    query = post_table.select().where(post_table.c.id.in_(post_ids))
    posts = await database.fetch_all(query)
    return await posts_with_extra_info(posts)


async def get_rating(post_id: int):
    query = sa.select(sa.func.avg(rating_table.c.rating)).where(rating_table.c.post_id == post_id)
    average = await database.fetch_val(query)
    return round(average, 2) if average is not None else None


async def get_user_by_id(user_id: int):
    query = user_table.select().where(user_table.c.id == user_id)
    user = await database.fetch_one(query)

    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user