from flask import Blueprint, render_template, request, redirect, url_for, flash
from . import db
from flask_login import login_user, logout_user, login_required, current_user
from .models import Postcategory, Trending, User, Post
import datetime

quiz = Blueprint("quiz", __name__)


@quiz.route("/")
def exam():
    posts = (
        Trending.query.filter(Trending.date_to_publish <= datetime.datetime.now())
        .order_by(Trending.date_to_publish.desc())
        .all()
    )
    return render_template("home.html", posts=posts, brand="Quiz")
