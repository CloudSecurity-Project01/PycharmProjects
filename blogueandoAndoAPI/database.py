import databases
import sqlalchemy
from blogueandoAndoAPI.config import config


metadata = sqlalchemy.MetaData()

user_table = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("email", sqlalchemy.String, unique=True, nullable=False),
    sqlalchemy.Column("password", sqlalchemy.String, nullable=False)
    )

post_table = sqlalchemy.Table(
    "posts",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("user_id", sqlalchemy.ForeignKey("users.id"), nullable=False),
    sqlalchemy.Column("title", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("content", sqlalchemy.String),
    sqlalchemy.Column("publication_date", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("public", sqlalchemy.Boolean, nullable=False, default=True)
)


rating_table = sqlalchemy.Table(
    "ratings",
    metadata,
    sqlalchemy.Column("user_id", sqlalchemy.ForeignKey("users.id"), primary_key=True, nullable=False),
    sqlalchemy.Column("post_id", sqlalchemy.ForeignKey("posts.id"), primary_key=True, nullable=False),
    sqlalchemy.Column("rating", sqlalchemy.Integer, nullable=False)
)

post_tag_table = sqlalchemy.Table(
    "posts_tags",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("tag_id", sqlalchemy.ForeignKey("tags.id"), nullable=False),
    sqlalchemy.Column("post_id", sqlalchemy.ForeignKey("posts.id"), nullable=False)
)

tag_table = sqlalchemy.Table(
    "tags",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("tag", sqlalchemy.String, nullable=False)
    )

engine = sqlalchemy.create_engine(
    config.DATABASE_URL, connect_args={"check_same_thread": False}
)

metadata.create_all(engine)
database = databases.Database(
    config.DATABASE_URL, force_rollback=config.DB_FORCE_ROLL_BACK
)
