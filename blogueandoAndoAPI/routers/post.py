from fastapi import APIRouter,  HTTPException
from blogueandoAndoAPI.models.post import PostIn, Post, MyPostIn, PostRating, PostTag
from blogueandoAndoAPI.models.tag import TagIn
from blogueandoAndoAPI.models.user import AuthenticationIn, Authentication
from blogueandoAndoAPI.routers.tag import get_tags, find_tags
from blogueandoAndoAPI.database import user_table, post_table,rating_table, post_tag_table, database
import datetime

router = APIRouter()


@router.post("/create_post", response_model=Post, status_code=201)
async def create_post(post: PostIn):
    post_dict = post.dict()
    data = {**post_dict, "publication_date": datetime.datetime.now().strftime("%D"), "public": True}
    query = post_table.insert().values(data)
    last_record_id = await database.execute(query)
    return {**data, "id": last_record_id, "rating": None, "tags": None}


@router.get("/posts", response_model=list[Post])
async def get_all_posts():
    query = post_table.select()
    all_posts = await database.fetch_all(query)
    print(all_posts)
    return await posts_with_extra_info(all_posts)


@router.get("/my_posts", response_model=list[Post])
async def get_my_posts(my_post: MyPostIn):
    query = post_table.select().where(post_table.c.user_id == my_post.user_id)
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
    #if rating > 3 or rating < 1: raise error
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
