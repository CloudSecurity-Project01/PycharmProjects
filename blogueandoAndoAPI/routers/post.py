from fastapi import APIRouter, HTTPException, Query
from blogueandoAndoAPI.models.post import PostIn, Post, MyPostIn, PostRating, PostTag
from blogueandoAndoAPI.models.tag import TagIn
from blogueandoAndoAPI.models.user import AuthenticationIn
from blogueandoAndoAPI.routers.tag import get_tags, find_tags
from blogueandoAndoAPI.helpers.database import user_table, post_table, rating_table, post_tag_table, database
from fastapi.security import OAuth2PasswordBearer
import datetime

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


@router.post("/create_post", response_model=Post, status_code=201)
async def create_post(post: PostIn):
    post_dict = post.dict()
    data = {**post_dict, "publication_date": datetime.datetime.now().strftime("%D"), "is_public": True}
    query = post_table.insert().values(data)
    last_record_id = await database.execute(query)
    user = await get_user_by_id(post.user_id)
    return {**data, "id": last_record_id, "rating": None, "tags": None, "user_name": user.name}

@router.get("/posts", response_model=list[Post])
async def get_all_posts():
    query = """
            SELECT p.*, u.name as user_name
            FROM posts p
            JOIN users u ON p.user_id = u.id
            WHERE p.is_public = 1
            """
    all_posts = await database.fetch_all(query)
    return await posts_with_extra_info(all_posts)

@router.get("/my_posts", response_model=list[Post])
async def get_my_posts(user_id: int = Query(...)):
    query = f"""
            SELECT p.*, u.name as user_name
            FROM posts p
            JOIN users u ON p.user_id = u.id
            WHERE p.user_id = {user_id}
            """
    my_posts = await database.fetch_all(query)
    return await posts_with_extra_info(my_posts)


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
    data = post.dict()
    # if rating > 3 or rating < 1: raise error
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
        average = round(all_ratings / len(ratings), 2)
        return average
    
async def get_user_by_id(user_id: int):
    query = user_table.select().where(user_table.c.id == user_id)
    return await database.fetch_one(query)

@router.post("/set_tag", response_model=Post)
async def add_tag(post: PostTag):
    data = post.dict()
    query = post_tag_table.insert().values(data)
    await database.execute(query)

    query = post_table.select().where(post_table.c.id == post.post_id)
    post = await database.fetch_one(query)
    return await post_with_extra_inf(post)

@router.get("/get_posts_tag", response_model=list[Post])
async def get_post_with_tags(tag: TagIn):
    tags = await find_tags(tag)
    if not tags:
        raise HTTPException(status_code=404, detail="Tag not found")

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
