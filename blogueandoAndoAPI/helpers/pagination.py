from sqlalchemy.sql import select, func
from blogueandoAndoAPI.helpers.database import database

async def paginate_query(base_query, size: int, skip: int):
    if size == -1:
        items = await database.fetch_all(base_query)
        return items, 1, 1, len(items)

    total_count_query = select(func.count()).select_from(base_query.alias("subquery"))
    total_count = await database.fetch_val(total_count_query)

    paginated_query = base_query.offset(skip).limit(size)
    items = await database.fetch_all(paginated_query)

    total_pages = (total_count // size) + (1 if total_count % size > 0 else 0)
    current_page = (skip // size) + 1

    return items, current_page, total_pages, total_count
