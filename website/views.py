from slugify import slugify
import string
import bbcode
import sqlalchemy
from . import ROWS_PER_PAGE
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    flash,
    session,
    url_for,
    abort,
)
from flask_login import current_user
from flask_login.utils import login_required

from .models import (
    Post,
    Trending,
    User,
    Postcategory,
    Comment,
    Save,
    Like,
    LikePost,
    SavePost,
    Viewed_post,
)

from . import db
import datetime

views = Blueprint("views", __name__)
ROWS_PER_PAGE = ROWS_PER_PAGE
bbcode = bbcode.render_html


@views.route("/")
def home():
    posts = (
        Trending.query.filter(Trending.date_to_publish <= datetime.datetime.now())
        .order_by(Trending.date_to_publish.desc())
        .all()
    )
    return render_template("home.html", posts=posts, brand="Home")


@views.route("/<string:data>/")
@views.route("/<string:data>/<int:page_v>/")
def menu(data, page_v=1):
    posts = Post.query.order_by(Post.date_to_publish.desc()).all()
    category_list = []
    category_s = Postcategory.query.filter().all()
    username = ""
    category_id = ""

    for item in category_s:
        category_list.append(item.name.lower())
        category_id = item.id if data.lower() == item.name.lower() else category_id
    category_exists = True if data.lower() in category_list else False

    user_s = User.query.filter_by(userlower=data.lower()).first()
    user_exists = True if user_s else False

    if category_exists:
        posts = (
            Post.query.filter(
                (Post.category == category_id)
                & (Post.date_to_publish <= datetime.datetime.now())
            )
            .order_by(
                Post.pin.desc(), Post.last_comment.desc(), Post.date_to_publish.desc()
            )
            .paginate(page=page_v, per_page=ROWS_PER_PAGE)
        )
        return render_template(
            "category.html", posts=posts, id=category_id, title=data.title()
        )
    elif user_exists:
        username = user_s.username
        user = User.query.filter_by(username=username).first()
        posts = Post.query.filter_by(author=user.id).limit(ROWS_PER_PAGE)
        return render_template("profile.html", user=user, posts=posts)
    return abort(404)


@views.route("/<int:data>/")
def postint(data):
    post_exists = Post.query.filter_by(id=data).first()
    if post_exists:
        slug = post_exists.slug
        return redirect(url_for("views.post", data=data, slug=slug))
    return abort(404)


@views.route("/<int:data>/<slug>/<int:page>")
@views.route("/<int:data>/<slug>")
def post(data, slug, page=1):
    post_exists = Post.query.filter_by(id=data).first()

    comments = Comment.query.filter_by(post=data).paginate(
        page=page, per_page=ROWS_PER_PAGE
    )
    if post_exists:
        slug = post_exists.slug
        date = datetime.datetime.now()
        # A new view
        post_exists.total_views = int(post_exists.total_views) + 1

        # Log into the database that this user view this page
        if current_user.is_authenticated:
            created = Viewed_post.query.filter(
                (Viewed_post.viewer_id == current_user.id)
                & (Viewed_post.post_id == data)
            ).first()
            page_v = 1 if not comments.pages else comments.pages
            comment_v = Comment.query.filter_by(post=data).paginate(
                page=page_v, per_page=ROWS_PER_PAGE
            )
            total = None if not len(comment_v.items) else (len(comment_v.items) - 1)
            last_viewed_id = 0 if total == None else comment_v.items[total].id
            already_viewed = current_user.has_viewed_ft_notif(data)
            if not already_viewed:
                if created:
                    created.last_comment_seen = last_viewed_id
                else:
                    viewed = Viewed_post(
                        viewer_id=current_user.id,
                        post_id=data,
                        last_comment_seen=last_viewed_id,
                        last_comment_pageid=page_v,
                    )
                    db.session.add(viewed)

        db.session.commit()

        return render_template(
            "post.html",
            data=data,
            post=post_exists,
            date=date,
            comments=comments,
            bbcode=bbcode,
        )
    return abort(404)


@views.route("/create-post/<int:id>", methods=["GET", "POST"])
@login_required
def createpost(id):
    if request.method == "POST":
        topic = request.form.get("topic")
        body = request.form.get("body")
        category = id
        slug = topic
        if not body or not topic:
            flash("Write something! You have that ability.")
        else:
            category_exists = Postcategory.query.filter_by(id=id).first()
            if category_exists:
                user_post = Post(
                    topic=string.capwords(topic),
                    body=body,
                    category=category,
                    author=current_user.id,
                    slug=slugify(slug),
                )
                db.session.add(user_post)
                db.session.commit()
                return redirect(
                    url_for("views.post", data=user_post.id, slug=user_post.slug)
                )
            else:
                flash("Category does not exist.")
    return render_template("createpost.html")


@views.route("/create-category/", methods=["GET", "POST"])
@login_required
def createcategory():
    if request.method == "POST":
        category = request.form.get("category")
        mod = current_user.id
        if not category:
            flash("Write something! You have that ability.")
        else:
            category = Postcategory(name=category, mod=mod)
            db.session.add(category)
            db.session.commit()
            return redirect(url_for("views.home"))

    postcategory = Postcategory.query.all()
    return render_template("createcategory.html", postcategory=postcategory)


@views.route("/comment/<int:id>", methods=["GET", "POST"])
def createcomment(id):
    quote = request.args.get("quote")

    if request.method == "POST":
        body = request.form.get("body")
        post = id
        post_exists = Post.query.filter_by(id=id).first()

        if post_exists:
            if not body:
                flash("Write something! You have that ability.")
            else:
                if current_user.is_anonymous:
                    username = request.form.get("user")
                    user_s = User.query.filter_by(userlower=username.lower()).first()
                    user_exists = True if user_s else False

                    def username_no_make_sense(u):
                        if " " in u:
                            flash("Username contains space.")
                            return True
                        elif u.isalnum() == False:
                            if u == "":
                                return False
                            else:
                                flash(
                                    "Only alphabets and numbers are allowed in the username."
                                )
                                return True
                        elif len(u) > 30:
                            flash(
                                f' The length of the username " {u}" not allowed, It should be less than 30.'
                            )
                            return True
                        else:
                            return False

                    if username_no_make_sense(username):
                        return render_template(
                            "createcomment.html", username=username, body=body
                        )
                    elif user_exists:
                        flash(
                            f' "{username}" is already a bonafide, registered member\'s username. \n Try another'
                        )
                        return render_template(
                            "createcomment.html", username=username, body=body
                        )
                    else:
                        name = (
                            "Anonymous"
                            if not request.form.get("user")
                            else request.form.get("user")
                        )
                        author = "Anonymous"
                else:
                    name = "User"
                    author = current_user.id
                user_comment = Comment(post=post, text=body, author=author, anon=name)
                db.session.add(user_comment)
                post_exists.last_comment = datetime.datetime.now()
                db.session.commit()
                return redirect(url_for("views.postint", data=post))
        else:
            flash("Post does not exist.")
    else:
        if quote and quote.isnumeric and request.args.get("page"):
            post_page = int(request.args.get("page"))
            type = request.args.get("post")
            comment = ""
            if type == "c":
                comment_exists = Comment.query.filter_by(id=int(quote)).first()
                comment = comment_exists.text
            elif type == "p":
                comment_exists = Post.query.filter_by(id=int(quote)).first()
                comment = comment_exists.body
            return render_template(
                "createcomment.html",
                quote=quote,
                comment=comment,
                comment_exists=comment_exists,
                type=type,
                page=post_page,
            )
    return render_template("createcomment.html")


@views.route("/all/")
def all():
    posts = Post.query.order_by(
        Post.last_comment.desc(), Post.date_to_publish.desc()
    ).all()
    return render_template("all.html", posts=posts)


@views.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    post_exists = Post.query.filter_by(id=id).first()
    if post_exists:
        if request.method == "POST":
            if current_user.id == post_exists.author:
                head = request.form.get("topic")
                body = request.form.get("body")
                post_exists.topic = head
                post_exists.body = body
                db.session.commit()
                return redirect(url_for("views.postint", data=id))
            else:
                flash(
                    "You are not the creator of this thread, you don't have permission to edit this post."
                )
    else:
        flash("Post does not exist")
    return render_template("editpost.html", post=post_exists)


@views.route("/editcomment/<int:id>/<int:page>", methods=["GET", "POST"])
@views.route("/editcomment/<int:id>", methods=["GET", "POST"])
@login_required
def editcomment(id, page=1):
    comment_exists = Comment.query.filter_by(id=id).first()
    if comment_exists:
        if request.method == "POST":
            topicid = comment_exists.post
            if current_user.id == comment_exists.author:
                body = request.form.get("body")
                # slug = comment_exists.post.slug
                comment_exists.text = body
                db.session.commit()
                return redirect(
                    url_for("views.post", data=topicid, page=page, slug="aa")
                    + "#"
                    + str(comment_exists.id)
                )
            else:
                flash(
                    "You are not the creator of this comment, you don't have permission to edit this post."
                )
    else:
        flash("Post does not exist")
    return render_template("editcomment.html", comment=comment_exists)


@views.route("/save/<string:type>/<int:id>/<int:page>")
@login_required
def save(id, type, page):
    postinit = Post.query.filter_by(id=id).first()
    slug = postinit.slug
    if type == "p":
        post_exists = Post.query.filter_by(id=id).first()
        if post_exists:
            jump = ""
            post = SavePost(user=current_user.id, postid=id)
            save_exists = SavePost.query.filter(
                (SavePost.postid == id) & (SavePost.user == current_user.id)
            ).first()
        else:
            flash("Post does not exists.")

    else:
        post_exists = Comment.query.filter_by(id=id).first()
        commentid = int(request.args.get("comment"))
        if post_exists:
            jump = f"#{commentid}"
            post = Save(user=current_user.id, postid=id, commentid=commentid)
            save_exists = Save.query.filter(
                (Save.postid == id)
                & (Save.commentid == commentid)
                & (Save.user == current_user.id)
            ).first()
        else:
            flash("Comment does not exists.")

    if save_exists:
        db.session.delete(save_exists)
        db.session.commit()
    else:
        db.session.add(post)
        db.session.commit()
    return redirect(url_for("views.post", data=id, slug=slug, page=page) + jump)


@views.route("/saved/")
@login_required
def saved():
    saved_post = SavePost.query.filter_by(user=current_user.id)
    saved_c = Save.query.filter_by(user=current_user.id)
    posts = (
        saved_post.union_all(saved_c)
        .filter(Save.user == current_user.id)
        .order_by(SavePost.date_to_publish.desc(), Save.date_to_publish.desc())
    )
    # posts = union_all(saved_c,saved_post)
    # posts=Save.query.join(SavePost,SavePost.user == Save.user).filter(Save.user==current_user.id).order_by(Save.date_to_publish.desc())

    return render_template(
        "saved.html", posts=posts, bbcode=bbcode, title="Saved Posts"
    )


@views.route("/like/<string:type>/<int:id>/<int:page>")
@login_required
def like(id, type, page):
    postinit = Post.query.filter_by(id=id).first()
    slug = postinit.slug
    if type == "p":
        post_exists = Post.query.filter_by(id=id).first()
        if post_exists:
            jump = ""
            post = LikePost(user=current_user.id, postid=id)
            like_exists = LikePost.query.filter(
                (LikePost.postid == id) & (LikePost.user == current_user.id)
            ).first()
        else:
            flash("Post does not exists.")

    else:
        post_exists = Comment.query.filter_by(id=id).first()
        commentid = int(request.args.get("comment"))
        if post_exists:
            jump = f"#{commentid}"
            post = Like(user=current_user.id, postid=id, commentid=commentid)
            like_exists = Like.query.filter(
                (Like.postid == id)
                & (Like.commentid == commentid)
                & (Like.user == current_user.id)
            ).first()
        else:
            flash("Comment does not exists.")

    if like_exists:
        db.session.delete(like_exists)
        db.session.commit()
    else:
        db.session.add(post)
        db.session.commit()
    return redirect(url_for("views.post", data=id, slug=slug, page=page) + jump)


@views.route("/shared")
@views.route("/shared/<int:page_v>/")
@login_required
def shared(page_v=1):
    current_user.last_seen_shared = datetime.datetime.now()
    db.session.commit()
    shared_post = current_user.shared_posts().paginate(
        page=page_v, per_page=ROWS_PER_PAGE
    )
    return render_template(
        "shared.html", title="Shared Posts", bbcode=bbcode, shared_post=shared_post
    )


@views.route("/followed")
@views.route("/followed/<int:page_v>/")
@login_required
def followed(page_v=1):
    current_user.last_seen_ft = datetime.datetime.now()
    db.session.commit()
    followed_topic = current_user.followed_posts().paginate(
        page=page_v, per_page=ROWS_PER_PAGE
    )
    return render_template(
        "followedtopic.html",
        title="Followed Topics",
        bbcode=bbcode,
        followed_topic=followed_topic,
    )


@views.route("/following/")
@views.route("/following/<int:page_v>/")
@login_required
def following(page_v=1):
    current_user.last_seen_following = datetime.datetime.now()
    db.session.commit()
    followings = current_user.followed_comments().paginate(
        page=page_v, per_page=ROWS_PER_PAGE
    )
    return render_template(
        "followedcomment.html", title="Following", bbcode=bbcode, followings=followings
    )


@views.route("/mention")
@views.route("/mention/<int:page_v>/")
@login_required
def mention(page_v=1):
    current_user.last_seen_mention = datetime.datetime.now()
    db.session.commit()
    mentions = current_user.new_mentions_view().paginate(
        page=page_v, per_page=ROWS_PER_PAGE
    )
    return render_template(
        "mention.html", title="Mention", bbcode=bbcode, mentions=mentions
    )


# @views.route("/cte")
# def cte():
#     cte_code = Comment.query.filter_by(post=1).cte(
#         recursive=True, name="recursive_franchisee"
#     )
#     first_run = sqlalchemy.orm.aliased(cte_code, name="F")
#     second_run = sqlalchemy.orm.aliased(Comment, name="S")
#     cte_code = cte_code.union_all(
#         second_run.query.filter_by(post=1).join(
#             first_run, first_run.c.id == second_run.id
#         )
#     )
#     the_func_to_run = Comment.query.filter_by(post=1)
#     stmt = sqlalchemy.select(["*"]).select_from(cte_code)
#     for x in dict(cte_code.c):
#         print(type(stmt))

#     return str(stmt)
