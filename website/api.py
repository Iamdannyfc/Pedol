from bdb import Breakpoint
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import null
from . import db
from flask_login import login_user, logout_user, login_required, current_user
from .models import LikePost, Comment, Like, Post, Trending, Shared
import datetime

api = Blueprint("api", __name__)


@api.route("/")
def exam():
    posts = (
        Trending.query.filter(Trending.date_to_publish <= datetime.datetime.now())
        .order_by(Trending.date_to_publish.desc())
        .all()
    )
    return render_template("home.html", posts=posts, brand="api")


@api.route("/like/<string:type>/<int:id>/<int:commentid>", methods=["POST"])
@login_required
def like(id, type, commentid):
    postinit = Post.query.filter_by(id=id).first()

    # This function will show the information needed in the json dict

    def json_info(obj):
        likes = obj.total_likes()
        liked = obj.i_have_liked()
        return {"likes": likes, "liked": liked}

    if type == "p":
        # Since it is a post, check if it exist and like
        post_exists = Post.query.filter_by(id=id).first()
        if post_exists:
            post = LikePost(user=current_user.id, postid=id)
            like_exists = LikePost.query.filter(
                (LikePost.postid == id) & (LikePost.user == current_user.id)
            ).first()

        else:
            return jsonify({"error": "Post does not exists."}, 400)

    else:
        # oh! it is a Comment, also check if it exist and like
        post_exists = Comment.query.filter_by(id=commentid).first()
        if post_exists:
            post = Like(user=current_user.id, postid=id, commentid=commentid)
            like_exists = Like.query.filter(
                (Like.postid == id)
                & (Like.commentid == commentid)
                & (Like.user == current_user.id)
            ).first()
        else:
            return jsonify({"error": "Comment does not exists."}, 400)

    if like_exists:
        db.session.delete(like_exists)
        db.session.commit()
    else:
        db.session.add(post)
        db.session.commit()
    return jsonify(json_info(post_exists))


# Share this post
@api.route("/share/<string:type>/<int:pid>/<int:cid>", methods=["POST"])
@login_required
def share(pid, type, cid):
    # This function will show the information needed in the json dict

    def json_info(shared):
        return {"shared": shared}

    postinit = Post.query.filter_by(id=pid).first()
    # This is the post whether topic or comment
    shared_pid = postinit.id

    # If it is a comment
    if cid and type == "c":
        # Find the Comment id
        shared_cid = Comment.query.filter_by(id=cid).first().id
        jump = f"#{shared_cid}"
        shared_post = Shared.query.filter(
            (Shared.user == current_user.id) & (Shared.commentid == cid)
        ).first()
    elif pid and type == "p":
        shared_cid = cid
        shared_post = Shared.query.filter(
            (Shared.user == current_user.id)
            & (Shared.commentid == 0)
            & (Shared.postid == shared_pid)
        ).first()

    else:
        return jsonify({"error": "Post does not exists."}, 400)

    if shared_post:
        db.session.delete(shared_post)
        db.session.commit()

    else:
        shared_post = Shared(
            user=current_user.id, postid=shared_pid, commentid=shared_cid
        )
        db.session.add(shared_post)
        db.session.commit()
    print(shared_post)

    if type == "p":
        print(current_user.has_shared_post(pid))
        sharedornot = (
            True if shared_pid in current_user.has_shared_post(shared_pid) else False
        )

    else:
        sharedornot = (
            True
            if shared_cid in current_user.has_shared_post(shared_pid, shared_cid)
            else False
        )
        print(current_user.has_shared_post(shared_pid, shared_cid))

    return jsonify(json_info(sharedornot))

    # ........................................


#     if type == "p":
#         # Since it is a post, check if it exist and like
#         post_exists = Post.query.filter_by(id=id).first()
#         if post_exists:
#             post = LikePost(user=current_user.id, postid=id)
#             like_exists = LikePost.query.filter(
#                 (LikePost.postid == id) & (LikePost.user == current_user.id)
#             ).first()

#         else:
#             return jsonify({"error": "Post does not exists."}, 400)

#     else:
#         # oh! it is a Comment, also check if it exist and like
#         post_exists = Comment.query.filter_by(id=commentid).first()
#         if post_exists:
#             post = Like(user=current_user.id, postid=id, commentid=commentid)
#             like_exists = Like.query.filter(
#                 (Like.postid == id)
#                 & (Like.commentid == commentid)
#                 & (Like.user == current_user.id)
#             ).first()
#         else:
#             return jsonify({"error": "Comment does not exists."}, 400)

#     if like_exists:
#         db.session.delete(like_exists)
#         db.session.commit()
#     else:
#         db.session.add(post)
#         db.session.commit()
#     return jsonify(json_info(post_exists))

# # Breakpoint
# def share(pid, cid=0, page=1):
#     postinit = Post.query.filter_by(id=pid).first()
#     slug = postinit.slug
#     # This is the post whether topic or comment
#     shared_pid = postinit.id

#     # If it is a comment
#     if cid:
#         # Find the Comment id
#         shared_cid = Comment.query.filter_by(id=cid).first().id
#         jump = f"#{shared_cid}"
#         shared_post = Shared.query.filter(
#             (Shared.user == current_user.id) & (Shared.commentid == cid)
#         ).first()
#     else:
#         jump = ""
#         shared_cid = cid
#         shared_post = Shared.query.filter(
#             (Shared.user == current_user.id)
#             & (Shared.commentid == 0)
#             & (Shared.postid == shared_pid)
#         ).first()

#     if shared_post:
#         db.session.delete(shared_post)
#         db.session.commit()
#     else:
#         shared_post = Shared(
#             user=current_user.id, postid=shared_pid, commentid=shared_cid
#         )
#         db.session.add(shared_post)
#         db.session.commit()
#     return redirect(url_for("views.post", data=pid, slug=slug, page=page) + jump)
