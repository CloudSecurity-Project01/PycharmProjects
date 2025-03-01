import os
from google.cloud.sql.connector import Connector, IPTypes
import sqlalchemy
from sqlalchemy import Column, Boolean, Integer, String, Float
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import pymysql
from dotenv import load_dotenv

Base = declarative_base()

load_dotenv()


def connect_with_connector(connector) -> sqlalchemy.engine.base.Engine:

    instance_connection_name = os.environ.get("INSTANCE_CONNECTION_NAME")
    db_user = os.getenv("DB_USER", "")
    db_pass = os.getenv("DB_PASS")
    db_name = os.getenv("DB_NAME")

    ip_type = IPTypes.PRIVATE if os.environ.get("PRIVATE_IP") else IPTypes.PUBLIC

    connector_args = {
        "cafile": 'cert.pem',
        "validate_host": False
    }

    def get_connection() -> pymysql.Connection:
        conn = connector.connect (
            instance_connection_name,
            "pymysql",
            user=db_user,
            password=db_pass,
            db=db_name,
            ip_type=ip_type,
        )
        return conn

    pool = sqlalchemy.create_engine(
        "mysql+pymysql://",
        creator=get_connection
    )
    return pool


class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), nullable=False)
    email = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    is_verified = Column(Boolean, nullable=False, default=False)


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    user_id = Column("user_id", sqlalchemy.ForeignKey("users.id"), nullable=False)
    title = Column(String(250), nullable=False)
    content = Column(String(500))
    content_location = Column(String(250))
    publication_date = Column(String(50), nullable=False)
    is_public = Column(Boolean, nullable=False, default=True)


class Rating(Base):
    __tablename__ = "ratings"

    user_id = Column(sqlalchemy.ForeignKey("users.id"), primary_key=True, nullable=False)
    post_id = Column(sqlalchemy.ForeignKey("posts.id"), primary_key=True, nullable=False)
    rating = Column(Float, nullable=False)


class Post_Tag(Base):
    __tablename__ = "posts_tags"

    tag_id = Column(sqlalchemy.ForeignKey("tags.id"), primary_key=True, nullable=False)
    post_id = Column(sqlalchemy.ForeignKey("posts.id"), primary_key=True, nullable=False)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    tag = Column(String(250), nullable=False)



# Initialize python connector and connection pool engine
connector = Connector()
engine = connect_with_connector(connector)
session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()


tables = [Post_Tag, Rating, Tag, Post, User]
inspect = sqlalchemy.inspect(engine)


def delete_tables():
    for table in tables:
        if inspect.has_table(table.__tablename__):
            table.__table__.drop(bind=engine)


def create_tables():
    for table in tables[::-1]:
        if not inspect.has_table(table.__tablename__):
            table.__table__.create(bind=engine)


def insert(table, entry):
    with engine.connect() as conn:
        new_entry = conn.execute(
            sqlalchemy.insert(table),
            [entry]
        )

        conn.commit()
        return new_entry


def fetch_one(table, condition):
    result = fetch_all(table, condition)
    if len(result) > 0: return result[0]
    return None


def fetch_all(table, condition):
    with engine.connect() as conn:
        all_entries = conn.execute(
            sqlalchemy.select(table)
            .where(condition)
        ).mappings().all()
        return all_entries


def fetch_one_query(query):
    result = fetch_all_query(query)
    if len(result) > 0: return result[0]
    return None

def fetch_all_query(query):
    with engine.connect() as conn:
        all_entries = conn.execute(
            query
        ).mappings().all()
        return all_entries


def update(table, condition, values):
    with engine.connect() as conn:
        conn.execute(
            sqlalchemy.update(table).where(condition).values(values)
        )
        conn.commit()


def delete(table, condition):
    with engine.connect() as conn:
        conn.execute(
            sqlalchemy.delete(table).where(condition)
        )
        conn.commit()


create_tables()

#update(User, User.id == 1, {User.is_verified: True})
#print(fetch_one(User, User.id == 2))
