from genericpath import exists
from os import name
from flask import Blueprint, render_template, request, redirect, url_for, flash

from website.views import postint
from . import db
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import Comment, Followed_posts, Postcategory, Shared, Trending, User, Post
import re
import datetime

auth = Blueprint("auth", __name__)


@auth.route("/login/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(userlower=username.lower()).first()
        user_exists = True if user else False
        if user_exists:
            if check_password_hash(user.password, password):
                login_user(user, remember=True)
                current_user.last_login = datetime.datetime.now()
                db.session.commit()
                return redirect(url_for("views.home"))
            else:
                flash("Password incorrect")
        else:
            flash("Username does not exist")
    return render_template("login.html")


@auth.route("/register/", methods=["GET", "POST"])
def register():
    username = ""
    email_req = ""
    if request.method == "POST":
        username = request.form.get("username")
        email_req = request.form.get("email")
        password = request.form.get("password")
        password1 = request.form.get("psw-repeat")
        regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

        def username_no_make_sense(u):
            if " " in u:
                flash("Username contains space.")
                return True
            elif u.isalnum() == False:
                flash("Only alphabets and numbers are allowed in the username.")
                return True
            elif len(u) < 2 or len(u) > 30:
                flash(
                    f' The length of the username " {u}" not allowed, It should be greater than 2 and less than 30.'
                )
                return True
            else:
                return False

        def password_no_make_sense(p):
            if len(p) < 2:
                return True
            else:
                return False

        def email_invalid(em):
            if re.fullmatch(regex, em):
                return False
            else:
                flash("Please register a valid email address.", category="error")
                return True

        user_s = User.query.filter_by(userlower=username.lower()).first()
        user_exists = True if user_s else False

        category_list = []
        category_s = Postcategory.query.filter().all()
        for item in category_s:
            category_list.append(item.name.lower())

        category_exists = True if username.lower() in category_list else False

        email_s = User.query.filter_by(email=email_req.lower()).first()
        email_exists = True if email_s else False

        if user_exists or category_exists:
            flash(f'Username "{username}" exists', category="error")
        elif email_exists:
            flash("Email exists", category="error")
        elif password != password1:
            flash("Password does not match", category="error")
        elif username_no_make_sense(username):
            pass
        elif password_no_make_sense(password1):
            flash(
                "Something is wrong with the password, it should greater than 2",
                category="error",
            )
        elif email_invalid(email_req):
            pass
        else:
            new_user = User(
                email=email_req,
                username=username,
                userlower=username.lower(),
                password=generate_password_hash(password, method="sha256"),
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            return redirect(url_for("views.home"))

    return render_template("register.html", username=username, email=email_req)


@auth.route("/logout/", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("views.home"))


@auth.route("/move-trending/<int:id>", methods=["POST"])
@login_required
def movetrending(id):
    post = Post.query.filter_by(id=id).first()
    if post:
        postid = post.id
        topic = post.topic
        slug = post.slug
        datetp = request.form.get("date")
        date_processing = datetp.replace("T", "-").replace(":", "-").split("-")
        date_processing = [int(v) for v in date_processing]
        date_out = datetime.datetime(*date_processing)
        post = Trending(postid=postid, name=topic, slug=slug, date_to_publish=date_out)
        db.session.add(post)
        db.session.commit()
        print(postid, topic, slug, date_out)
    return redirect(url_for("views.home"))


@auth.route("/follow/<int:userid>")
@login_required
def follow(userid):
    exists = User.query.filter_by(id=userid).first()
    fexists = current_user.is_following(exists)
    if not exists:
        flash("Cannot follow this user since it does not exist.")
        return redirect(url_for("views.home"))
    elif fexists:
        current_user.unfollow(exists)
        db.session.commit()
    else:
        current_user.follow(exists)
        db.session.commit()
    return redirect(url_for("views.menu", data=exists.username))


@auth.route("/share/<int:page>/<int:pid>/<int:cid>")
@auth.route("/share/<int:page>/<int:pid>")
@login_required
def share(pid, cid=0, page=1):
    postinit = Post.query.filter_by(id=pid).first()
    slug = postinit.slug
    # This is the post whether topic or comment
    shared_pid = postinit.id

    # If it is a comment
    if cid:
        # Find the Comment id
        shared_cid = Comment.query.filter_by(id=cid).first().id
        jump = f"#{shared_cid}"
        shared_post = Shared.query.filter(
            (Shared.user == current_user.id) & (Shared.commentid == cid)
        ).first()
    else:
        jump = ""
        shared_cid = cid
        shared_post = Shared.query.filter(
            (Shared.user == current_user.id)
            & (Shared.commentid == 0)
            & (Shared.postid == shared_pid)
        ).first()

    if shared_post:
        db.session.delete(shared_post)
        db.session.commit()
    else:
        shared_post = Shared(
            user=current_user.id, postid=shared_pid, commentid=shared_cid
        )
        db.session.add(shared_post)
        db.session.commit()
    return redirect(url_for("views.post", data=pid, slug=slug, page=page) + jump)


@auth.route("/followpost/<int:postid>")
@login_required
def followpost(postid):
    exists = Post.query.filter_by(id=postid).first()
    fexists = current_user.is_following_post(exists)
    if not exists:
        flash("Cannot follow this post since it does not exist.")
        return redirect(url_for("views.home"))
    elif fexists:
        current_user.unfollow_post(exists)
        db.session.commit()
    else:
        current_user.follow_post(exists)
        db.session.commit()
    return redirect(url_for("views.menu", data=current_user.username))
