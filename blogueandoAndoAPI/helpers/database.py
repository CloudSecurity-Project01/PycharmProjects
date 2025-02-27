import databases
import os
from google.cloud.sql.connector import Connector, IPTypes
import sqlalchemy
from sqlalchemy import Column, Boolean, Integer, String, Float
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import pymysql

Base = declarative_base()


def connect_with_connector(connector) -> sqlalchemy.engine.base.Engine:

    instance_connection_name = "cloudsecurity-project01-202510:us-central1:db-blogueando-ando-2025" #os.environ[]
    db_user = "admin" #os.environ.get("DB_USER", "")
    db_pass = "Diana!23" #os.environ["DB_PASS"]
    db_name = "posts"#os.environ["DB_NAME"]

    ip_type = IPTypes.PRIVATE if os.environ.get("PRIVATE_IP") else IPTypes.PUBLIC

    connector_args = {
        "cafile": 'cert.pem',
        "validate_host": False,
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

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), nullable=False)
    email = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    verified = Column(Boolean, nullable=False, default=False)


class Post(Base):
    __tablename__ = "posts"

    post_id = Column(Integer, primary_key=True)
    user_id = Column("user_id", sqlalchemy.ForeignKey("users.user_id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(String)
    publication_date = Column(String, nullable=False)
    public = Column(Boolean, nullable=False, default=True)


class Rating(Base):
    __tablename__ = "ratings"

    user_id = Column(sqlalchemy.ForeignKey("users.user_id"), primary_key=True, nullable=False)
    post_id = Column(sqlalchemy.ForeignKey("posts.post_id"), primary_key=True, nullable=False)
    rating = Column(Float, nullable=False)

class Post_Tag(Base):
    __tablename__ = "posts_tags"

    post_tag_id = Column(Integer, primary_key=True)
    tag_id = Column(sqlalchemy.ForeignKey("tags.tag_id"), primary_key=True, nullable=False)
    post_id = Column(sqlalchemy.ForeignKey("posts.post_id"), primary_key=True, nullable=False)

class Tag(Base):
    __tablename__ = "tags"

    tag_id = Column(Integer, primary_key=True)
    tag = Column(String, nullable=False)


#engine = sqlalchemy.create_engine(
#    config.DATABASE_URL, connect_args={"check_same_thread": False}
#)

#metadata.create_all(engine)
#database = databases.Database(
#    config.DATABASE_URL, force_rollback=config.DB_FORCE_ROLL_BACK
#)

# Initialize python connector and connection pool engine
connector = Connector()
engine = connect_with_connector(connector)
database = sessionmaker(autocommit=False, autoflush=False, bind=engine)()


#User.__table__.drop(bind=engine)
#User.__table__.create(bind=engine)
