# from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager
from flask_ckeditor import CKEditor
import datetime
from werkzeug.security import generate_password_hash

db = SQLAlchemy()
ckeditor = CKEditor()
DB_NAME = "database.db"
SITE_NAME = "Pedclass"
ROWS_PER_PAGE = 20


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "secret key"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_NAME}"
    db.init_app(app)
    ckeditor.init_app(app)

    from .views import views
    from .auth import auth
    from .quora import quora
    from .quiz import quiz
    from .api import api

    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/")
    app.register_blueprint(quora, url_prefix="/c")
    app.register_blueprint(quiz, url_prefix="/q")
    app.register_blueprint(api, url_prefix="/api")

    from .models import (
        User,
        Post,
        Postcategory,
        Trending,
        Comment,
        Anonymous,
        Save,
        SavePost,
        LikePost,
    )

    create_database(app)

    @app.context_processor
    def base():
        def get_timedelta_in_seconds(s: int):
            return datetime.timedelta(seconds=s)

        def mydate():
            return datetime.datetime.now().strftime("%Y")

        def get_post(id: int):
            return (
                Post.query.with_entities(Post.topic, Post.category, Post.slug)
                .filter_by(id=id)
                .first()
            )

        return dict(
            MYDATE=mydate(),
            SITENAME=SITE_NAME,
            get_post=get_post,
            get_timedelta_in_seconds=get_timedelta_in_seconds,
        )

    login_manager = LoginManager()
    login_manager.login_message = "You have to login, to view this page"
    login_manager.login_view = "auth.login"
    login_manager.anonymous_user = Anonymous
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app


def create_database(app):
    if not path.exists("website/" + DB_NAME):
        db.create_all(app=app)
