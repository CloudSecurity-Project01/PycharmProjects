from fastapi import APIRouter, HTTPException, Query, Depends
from blogueandoAndoAPI.models.post import PostIn, Post, Pagination, PostRating, PostTag
from blogueandoAndoAPI.models.tag import TagIn
from blogueandoAndoAPI.routers.tag import get_tags, find_tags, validate_post_existence
from blogueandoAndoAPI.helpers.database import user_table, post_table, rating_table, post_tag_table, database, tag_table
from blogueandoAndoAPI.helpers.security import get_current_user_optional, get_current_user
from fastapi.security import OAuth2PasswordBearer
from typing import List, Optional
import sqlalchemy as sa
import datetime

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@router.post("/create_post", response_model=Post, status_code=201)
async def create_post(post: PostIn, current_user: dict = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    post_dict = post.model_dump()
    data = {**post_dict, "publication_date": datetime.datetime.now().strftime("%D"), "is_public": True, "user_id": current_user.id}

    query = post_table.insert().values(data)
    last_record_id = await database.execute(query)
    
    return {**data, "id": last_record_id, "rating": None, "tags": None, "user_name": current_user.user_name}



@router.get("/posts", response_model=List[Post])
async def get_all_posts(size: int, skip: int, current_user: Optional[dict] = Depends(get_current_user_optional)):
    query = (
        sa.select(post_table, user_table.c.name.label("user_name"))
        .join(user_table, post_table.c.user_id == user_table.c.id)
        .where(
            sa.or_(
                post_table.c.is_public == True,
                ((current_user is not None) and (post_table.c.user_id == current_user["id"]))
            )
        )
        .offset(skip)
        .limit(size)
    )
    all_posts = await database.fetch_all(query)
    return await posts_with_extra_info(all_posts)


@router.get("/my_posts", response_model=List[Post])
async def get_my_posts(size: int, skip: int, current_user: dict = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user_id = current_user["id"]

    query = (
        sa.select(post_table, user_table.c.name.label("user_name"))
        .join(user_table, post_table.c.user_id == user_table.c.id)
        .where(post_table.c.user_id == user_id)
        .offset(skip)
        .limit(size)
    )
    my_posts = await database.fetch_all(query)
    return await posts_with_extra_info(my_posts)


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
        raise HTTPException(status_code=404, detail="Post not found")
    
    return await post_with_extra_inf(post)


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

    data = post.model_dump()
    if data["rating"] > 5 or data["rating"] < 1:
        raise HTTPException(status_code=406, detail="Rating value is out of range")
    query = rating_table.insert().values(data)
    await database.execute(query)
    return post


async def get_rating(post_id: int):
    query = rating_table.select().where(rating_table.c.post_id == post_id)
    ratings = await database.fetch_all(query)
    if len(ratings) == 0:
        return None
    else:
        all_ratings = 0
        for r in ratings:
            all_ratings += r["rating"]
        average = round(all_ratings / len(ratings))
        return average
    

async def get_user_by_id(user_id: int):
    query = user_table.select().where(user_table.c.id == user_id)
    user = await database.fetch_one(query)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/set_tags", response_model=Post)
async def add_tags(post: PostTag):
    try:
        await validate_post_existence(post.post_id)
    except Exception as exception:
        raise exception

    tag_ids = []
    for tag_name in post.tags:
        tag_data = {"tag": tag_name}
        
        query = tag_table.select().where(tag_table.c.tag == tag_name)
        existing_tag = await database.fetch_one(query)

        if existing_tag:
            tag_id = existing_tag["id"]
        else:
            query = tag_table.insert().values(tag_data)
            tag_id = await database.execute(query)
        
        tag_ids.append(tag_id)

    for tag_id in tag_ids:
        query = post_tag_table.select().where(
            (post_tag_table.c.post_id == post.post_id) & (post_tag_table.c.tag_id == tag_id)
        )
        existing_post_tag = await database.fetch_one(query)

        if not existing_post_tag:
            query = post_tag_table.insert().values(post_id=post.post_id, tag_id=tag_id)
            await database.execute(query)

    query = post_table.select().where(post_table.c.id == post.post_id)
    post = await database.fetch_one(query)
    
    return await post_with_extra_inf(post)


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
