from fastapi import APIRouter, HTTPException, Query, Depends
from blogueandoAndoAPI.models.post import PostIn, Post, PostRating, PostTag, PostUpload
from blogueandoAndoAPI.models.tag import TagIn
from blogueandoAndoAPI.routers.tag import get_tags, find_tags, validate_post_existence, assign_tags_to_post
from blogueandoAndoAPI.helpers.database import Post as post_table
from blogueandoAndoAPI.helpers.database import insert, fetch_one, fetch_all_query, fetch_one_query, fetch_all, update, delete
from blogueandoAndoAPI.helpers.database import User as user_table
from blogueandoAndoAPI.helpers.database import Tag as tag_table
from blogueandoAndoAPI.helpers.database import Post_Tag as post_tag_table
from blogueandoAndoAPI.helpers.database import Rating as rating_table
from blogueandoAndoAPI.helpers.security import get_current_user_optional, get_current_user
from blogueandoAndoAPI.helpers.pagination import paginate_query
from blogueandoAndoAPI.helpers.storage import upload_post, get_post_content, delete_file
from fastapi.security import OAuth2PasswordBearer
from typing import Optional, Dict, Any, List
import sqlalchemy as sa
import datetime
import uuid

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@router.post("/post", response_model=Post, status_code=201)
async def create_post(post: PostIn, current_user: dict = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="No estás autorizado para realizar esta acción")

    content_id = str(uuid.uuid4())
    folder = str(current_user.id)
    location = f"{folder}/posts/{content_id}.html"

    upload_success = await upload_post(location, post.content)

    if not upload_success:
        raise HTTPException(status_code=500, detail="Hubo un error guardando el contenido de tu publicación")

    post_dict = post.model_dump()
    tags = post_dict.pop("tags", [])

    data = {
        **post_dict,
        "content": str(post.content)[:500],
        "content_location": location,
        "publication_date": datetime.datetime.now().strftime("%D"),
        "is_public": True,
        "user_id": current_user.id,
    }

    new_post = insert(
        post_table,
        data
    )

    last_record_id = new_post.lastrowid

    if tags:
        assign_tags_to_post(last_record_id, tags)

    post_data = fetch_one(
        post_table,
        post_table.id == last_record_id
    )

    return {**post_with_extra_inf(post_data), "content": post.content, "user_name": current_user.user_name}


@router.get("/posts", response_model=Dict[str, Any])
async def get_posts(
    size: int, 
    skip: int, 
    filter: str = "all",  
    tags: Optional[List[str]] = Query(None),
    tag_filter_mode: str = Query("and", regex="^(and|or)$"),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    base_query = sa.select(post_table, user_table.name.label("user_name")).join(
        user_table, post_table.user_id == user_table.id
    )

    if filter == "mine":
        if current_user is None:
            raise HTTPException(status_code=401, detail="No estás autorizado para realizar esta acción")
        user_id = current_user["id"]
        base_query = base_query.where(post_table.user_id == user_id)
    else:
        base_query = base_query.where(
            sa.or_(
                post_table.is_public == True,
                ((current_user is not None) and (post_table.user_id == current_user["id"]))
            )
        )

    if tags:
        tag_subquery = sa.select(post_tag_table.post_id).join(
            tag_table, tag_table.id == post_tag_table.tag_id
        )

        if tag_filter_mode == "and":
            for tag in tags:
                base_query = base_query.where(
                    post_table.id.in_(
                        tag_subquery.where(tag_table.tag == tag)
                    )
                )
        else:
            base_query = base_query.where(
                post_table.id.in_(
                    tag_subquery.where(tag_table.tag.in_(tags))
                )
            )

    posts, current_page, total_pages, total_items = await paginate_query(base_query, size, skip)

    return {
        "posts": posts_with_extra_info(posts),
        "current_page": current_page,
        "total_pages": total_pages,
        "total_items": total_items
    }


@router.get("/posts_ids", response_model=List[int])
async def get_visible_post_ids(filter: str = "all", current_user: Optional[dict] = Depends(get_current_user_optional)):
    base_query = sa.select(post_table.id)

    if filter == "mine":
        if not current_user:
            return []
        base_query = base_query.where(post_table.user_id == current_user["id"])
    else:
        base_query = base_query.where(
            sa.or_(
                post_table.is_public == True,
                ((current_user is not None) and (post_table.user_id == current_user["id"]))
            )
        )

    result = fetch_all_query(base_query)
    post_ids = [row["id"] for row in result]

    return post_ids

@router.get("/post", response_model=Post)
async def get_post(id: int = Query(...), current_user: Optional[dict] = Depends(get_current_user_optional)):
    query = (
        sa.select(post_table, user_table.name.label("user_name"))
        .join(user_table, post_table.user_id == user_table.id)
        .where(post_table.id == id)
        .where(
            sa.or_(
                post_table.is_public == True,
                ((current_user is not None) and (post_table.user_id == current_user["id"]))
            )
        )
    )
    post = fetch_one_query(query)

    if not post:
        raise HTTPException(status_code=404, detail="No se encontró la publicación")
    
    post_dict = post_with_extra_inf(post)

    content_location = post_dict.get("content_location")
    if content_location:
        post_dict["content"] = await get_post_content(content_location)

    return post_dict


@router.put("/post/{post_id}", response_model=Post)
async def update_post(post_id: int, post: PostIn, current_user: dict = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="No estás autorizado para realizar esta acción")

    query = post_table.select().where(post_table.id == post_id)
    existing_post = fetch_one_query(query)

    if existing_post is None:
        raise HTTPException(status_code=404, detail="No se encontró la publicación")

    if existing_post["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para editar esta publicación")

    file_name = existing_post["content_location"]
    if not file_name:
        raise HTTPException(status_code=500, detail="No se encontró el archivo de contenido asociado")

    upload_success = await upload_post(file_name, post.content_location)
    if not upload_success:
        raise HTTPException(status_code=500, detail="Error al actualizar el contenido en almacenamiento")

    updated_data = {
        post_table.title: post.title,
        post_table.is_public: post.is_public,
        post_table.content: str(post.content)[:500]
    }

    update(
        post_table,
        post_table.id == post_id,
        updated_data
    )

    if post.tags is not None:
        assign_tags_to_post(post_id, post.tags)

    rating = get_rating(post_id)

    updated_post = {
        **updated_data,
        "id": post_id,
        "content": post.content,
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

    existing_post = fetch_one(
        post_table,
        post_table.id == post_id
    )
    if existing_post is None:
        raise HTTPException(status_code=404, detail="No se encontró la publicación")

    if existing_post["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar esta publicación")

    content_location = existing_post["content_location"]

    query = post_tag_table.select().where(post_tag_table.post_id == post_id)
    post_tags = fetch_all(
        post_tag_table,
        post_tag_table.post_id == post_id
    )

    delete(post_tag_table, post_tag_table.post_id == post_id)

    for post_tag in post_tags:
        tag_id = post_tag["tag_id"]
        query = sa.select(post_tag_table.post_id).where(post_tag_table.tag_id == tag_id)
        remaining_posts = fetch_all_query(query)
        if not remaining_posts:
            delete(tag_table, tag_table.id == tag_id)

    delete(post_table, post_table.id == post_id)

    if content_location:
        deletion_success = await delete_file(content_location)
        if not deletion_success:
            print(f"Advertencia: No se pudo eliminar el archivo {content_location}")

    return {"detail": "Publicación eliminada con éxito"}


from concurrent.futures import ThreadPoolExecutor


def post_with_extra_inf(post):
    rating = get_rating(post["id"])
    tags = get_tags(post["id"])

    tag = []
    for t in tags:
        tag.append(t["tag"])
    return {**post, "rating": rating, "tags": tag}


def posts_with_extra_info(posts):
    with ThreadPoolExecutor(16) as executor:
        executors = []
        for post in posts:
            a = executor.submit(post_with_extra_inf, post)
            executors += [a]

        return [exc.result() for exc in executors]


@router.post("/set_rating", response_model=Post)
async def post_rating(post: PostRating, current_user: dict = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="No está autorizado para calificar esta publicación")

    post_data = fetch_one(
        post_table,
        post_table.id == post.post_id
    )

    if post_data is None:
        raise HTTPException(status_code=404, detail="No se encontró la publicación")

    if post_data["user_id"] == current_user.id:
        raise HTTPException(status_code=403, detail="No puedes calificar tu propia publicación")

    post_owner = fetch_one(
        user_table,
        user_table.id == post_data["user_id"]
    )

    if not post_owner:
        raise HTTPException(status_code=404, detail="No se encontró el usuario propietario de la publicación")

    existing_rating = fetch_one(
        rating_table,
        (rating_table.post_id == post.post_id)
        & (rating_table.user_id == current_user.id)
    )

    if existing_rating:
        raise HTTPException(status_code=409, detail="Ya has calificado esta publicación")

    if post.rating > 5 or post.rating < 1:
        raise HTTPException(status_code=406, detail="El valor de la calificación está fuera del rango permitido")

    data = {
        "post_id": post.post_id,
        "user_id": current_user.id,
        "rating": post.rating,
    }

    insert(
        rating_table,
        data
    )

    return {**post_with_extra_inf(post_data), "user_name": post_owner["name"]}


@router.post("/set_tags", response_model=Post)
async def add_tags(post: PostTag, current_user: dict = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Debe esta autenticado para agregar tags")

    validate_post_existence(post.post_id)
    assign_tags_to_post(post.post_id, post.tags)

    post_data = fetch_one(
        post_table,
        post_table.id == post.post_id
    )

    post_owner = fetch_one(
        user_table,
        user_table.id == current_user.id
    )
    
    return {**post_with_extra_inf(post_data), "user_name": post_owner["name"]}


@router.get("/get_posts_tag", response_model=list[Post])
async def get_post_with_tags(tag: TagIn):
    tags = await find_tags(tag)
    if len(tags) == 0:
        return []

    tag_ids = []
    for i in tags:
        tag_ids.append(i["id"])

    post_tags = fetch_all(
        post_tag_table,
        post_tag_table.tag_id.in_(tag_ids)
    )

    post_ids = []
    for i in post_tags:
        post_ids.append(i["post_id"])

    query = sa.select(post_table, user_table.name.label("user_name"))\
        .join(user_table, post_table.user_id == user_table.id)\
        .where(post_table.id.in_(post_ids))
    posts = fetch_all_query(
        query
    )
    return posts_with_extra_info(posts)


def get_rating(post_id: int):
    query = sa.select(sa.func.avg(rating_table.rating)).where(rating_table.post_id == post_id)
    average = fetch_one_query(query)["avg_1"]
    return round(average, 2) if average is not None else None


async def get_user_by_id(user_id: int):
    query = user_table.select().where(user_table.id == user_id)
    user = fetch_one(
        user_table,
        user_table.id == user_id
    )

    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

@router.post("/upload", status_code=200)
async def uploadPost(data: PostUpload):
    success = await upload_post(data.filename, data.content)
    if not success:
        raise HTTPException(status_code=500, detail="No se pudo subir el post. Inténtalo más tarde.")

@router.get("/download", status_code=200)
async def downloadPost(filename):
    return get_post_content(filename)    
