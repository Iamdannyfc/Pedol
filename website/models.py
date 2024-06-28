from ast import Or
from enum import unique
from sqlalchemy.orm import backref, relationship
from sqlalchemy.sql.expression import intersect, null
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.sql import func, functions
from . import db, ROWS_PER_PAGE
from flask_login import UserMixin, AnonymousUserMixin, current_user
from datetime import date, datetime

followers = db.Table(
    "followers",
    db.Column("follower_id", db.Integer, db.ForeignKey("user.id")),
    db.Column("followed_id", db.Integer, db.ForeignKey("user.id")),
)


class Viewed_post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    viewer_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"))
    last_comment_seen = db.Column(
        db.Integer, db.ForeignKey("comment.id"), nullable=True
    )
    last_comment_pageid = db.Column(db.Integer)
    date_created = db.Column(db.DateTime, default=datetime.now)


class Followed_posts(db.Model):
    __tablename__ = "followed_posts"
    follower_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    followed_post_id = db.Column(db.Integer, db.ForeignKey("post.id"), primary_key=True)
    follow_type = db.Column(db.Integer, default=1)
    post = db.relationship("Post")


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True)
    userlower = db.Column(db.String(10), unique=True)
    email = db.Column(db.String(150), unique=True)
    # signature = db.Column(db.String(150) ,nullable=True)
    password = db.Column(db.String(150))
    date_created = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime, default=datetime.now)
    last_seen_shared = db.Column(db.DateTime, default=datetime.now)
    last_seen_ft = db.Column(db.DateTime, default=datetime.now)
    last_seen_following = db.Column(db.DateTime, default=datetime.now)
    last_seen_mention = db.Column(db.DateTime, default=datetime.now)

    posts = db.relationship("Post", backref="user", passive_deletes=True)
    Postcategory = db.relationship("Postcategory", backref="user", passive_deletes=True)
    Comment = db.relationship(
        "Comment", backref="user", passive_deletes=True, overlaps="Comment,user"
    )
    share = db.relationship("Shared", backref="sharer", passive_deletes=True)

    # Testing

    followed = db.relationship(
        "User",
        secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref("followers", lazy="dynamic"),
        lazy="dynamic",
    )
    followed_post_by_user = relationship("Followed_posts", lazy="dynamic")

    # User Follow and Unfollows
    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    # Important user following functions
    def followed_posts(self):

        topic_followed = Post.query.join(
            Followed_posts, (Followed_posts.followed_post_id == Post.id)
        ).filter(
            (Followed_posts.follower_id == self.id) & (Followed_posts.follow_type == 1)
        )

        intersect = Post.query.join(
            Followed_posts, (Followed_posts.followed_post_id == Post.id)
        ).filter(
            (Followed_posts.follower_id == self.id) & (Followed_posts.follow_type == 2)
        )
        list = [int(id.id) for id in intersect]

        user_followed_topic = Post.query.join(
            followers, (followers.c.followed_id == Post.author)
        ).filter((followers.c.follower_id == self.id) & (Post.id.not_in(list)))
        total = topic_followed.union_all(user_followed_topic)
        return total

    def shared_posts(self):
        return (
            Shared.query.join(followers, (followers.c.followed_id == Shared.user))
            .filter(followers.c.follower_id == self.id)
            .order_by(Shared.date_to_publish.desc())
        )

    def followed_comments(self):
        comment = (
            Comment.query.join(followers, (followers.c.followed_id == Comment.author))
            .filter(followers.c.follower_id == self.id)
            .order_by(Comment.date_to_publish.desc())
        )
        # joined = post.join(comment, full=True)
        return comment

    def has_shared_post(self, shared_pid, shared_cid=0):
        if shared_cid:
            shared = Shared.query.filter(
                (Shared.user == self.id)
                & (Shared.commentid == shared_cid)
                & (Shared.postid == shared_pid)
            )
        else:
            shared = Shared.query.filter(
                (Shared.user == self.id)
                & (Shared.commentid == 0)
                & (Shared.postid == shared_pid)
            )

        def list_the_id(obj):
            if shared_cid:
                return obj.commentid
            else:
                return obj.postid

        shared = list(map(list_the_id, shared))

        return shared

    def is_following_post(self, post):
        intersect = Post.query.join(
            Followed_posts, (Followed_posts.followed_post_id == Post.id)
        ).filter(
            (Followed_posts.follower_id == self.id) & (Followed_posts.follow_type == 2)
        )
        list = [int(id.id) for id in intersect]

        user_followed_topic = Post.query.join(
            followers, (followers.c.followed_id == Post.author)
        ).filter((followers.c.follower_id == self.id) & (Post.id.not_in(list)))
        return (
            self.followed_post_by_user.filter(
                (Followed_posts.followed_post_id == post.id)
                & (Followed_posts.follower_id == self.id)
                & (Followed_posts.follow_type == 1)
            ).count()
            > 0
        ) or (user_followed_topic.filter(Post.id == post.id).count() > 0)

    def follow_post(self, post):
        if not self.is_following_post(post):
            theclass = Followed_posts.query.filter(
                (Followed_posts.followed_post_id == post.id)
                & (Followed_posts.follower_id == self.id)
                & (Followed_posts.follow_type == 2)
            ).first()
            if theclass:
                theclass.follow_type = 1
            else:
                theclass = Followed_posts()
                theclass.follow_type = 1
                theclass.followed_post_id = post.id
                self.followed_post_by_user.append(theclass)

    def unfollow_post(self, post):
        if self.is_following_post(post):
            theclass = Followed_posts.query.filter(
                (Followed_posts.followed_post_id == post.id)
                & (Followed_posts.follower_id == self.id)
                & (Followed_posts.follow_type == 1)
            ).first()
            if not theclass:
                theclass = Followed_posts()
                theclass.follow_type = 1
                theclass.followed_post_id = post.id
                self.followed_post_by_user.append(theclass)
                db.session.commit()
                theclass = Followed_posts.query.filter(
                    (Followed_posts.followed_post_id == post.id)
                    & (Followed_posts.follower_id == self.id)
                    & (Followed_posts.follow_type == 1)
                ).first()
            theclass.follow_type = 2

    # New Alerts on posts
    def new_shared(self):
        return self.shared_posts().filter(
            Shared.date_to_publish > self.last_seen_shared
        )

    def new_ft(self):
        return (
            Post.query.join(followers, (followers.c.followed_id == Post.author))
            .filter(followers.c.follower_id == self.id)
            .filter(Post.date_to_publish > self.last_seen_ft)
            .order_by(Post.date_to_publish.desc())
        )

    def new_followed_comment(self):
        comment = Comment.query.join(
            followers, (followers.c.followed_id == Comment.author)
        ).filter(
            (followers.c.follower_id == self.id)
            & (Comment.date_to_publish > self.last_seen_following)
        )
        return comment

    def new_ft_comment(self):
        intersect = self.followed_posts()
        list = [int(id.id) for id in intersect]
        comment = Comment.query.filter(
            Comment.post.in_(list) & (Comment.date_to_publish > self.last_seen_ft)
        )
        return comment

    def new_ft_comment_id(self, post_id):
        comment = (
            self.new_ft_comment()
            .filter(Comment.post == post_id)
            .order_by(Comment.date_to_publish)
        )
        return comment

    def has_viewed_ft_notif(self, post):
        comments = Comment.query.filter_by(post=post).paginate(per_page=ROWS_PER_PAGE)
        page = 1 if not comments.pages else comments.pages
        comments = Comment.query.filter_by(post=post).paginate(
            page=page, per_page=ROWS_PER_PAGE
        )
        total = None if not len(comments.items) else (len(comments.items) - 1)
        # total = None if not comments.total else comments.total - 1
        last_viewed_id = 0 if total == None else comments.items[total].id
        already_viewed = Viewed_post.query.filter(
            (Viewed_post.viewer_id == self.id)
            & (Viewed_post.last_comment_seen == last_viewed_id)
            & (Viewed_post.post_id == post)
        )
        return already_viewed.first()

    def viewed(self, post):
        # This code deals with the next comment id.........
        last_viewed = Viewed_post.query.filter(
            (Viewed_post.post_id == post) & (Viewed_post.viewer_id == self.id)
        ).first()
        if last_viewed:
            comment_id = (
                Comment.query.filter(
                    (Comment.post == post)
                    & (Comment.id > last_viewed.last_comment_seen)
                )
                .paginate(page=last_viewed.last_comment_pageid, per_page=ROWS_PER_PAGE)
                .items[0]
                .id
            )

            # While this code deals with its page id....
            comments = (
                Comment.query.filter_by(post=post)
                .paginate(page=last_viewed.last_comment_pageid, per_page=ROWS_PER_PAGE)
                .items
            )
            list = [int(id.id) for id in comments]
            page_num = (
                last_viewed.last_comment_pageid
                if comment_id in list
                else (last_viewed.last_comment_pageid + 1)
            )
            return {"page_num": page_num, "id": comment_id, "views_created": 1}
        else:
            return {"views_created": 0}

    def new_mentions(self):
        # mention = (
        #     Comment.query.filter(
        #         (Comment.text.ilike("% " + self.username + " %"))
        #         | (Comment.text.ilike("% " + "@" + self.username + " %"))
        #         | (Comment.text.ilike("@" + self.username))
        #         | (Comment.text.ilike(self.username))
        #         | (Comment.text.ilike("@" + self.username + " %"))
        #         | (Comment.text.ilike(self.username + " %"))
        #         | (Comment.text.ilike("% " + "@" + self.username))
        #         | (Comment.text.ilike("% " + self.username))
        #         | (Comment.text.ilike("%," + self.username))
        #         | (Comment.text.ilike("% " + self.username + ",%"))
        #         | (Comment.text.ilike("%," + self.username + "."))
        #         | (Comment.text.ilike("%," + self.username + ",%"))
        #         | (Comment.text.ilike("%," + "@" + self.username))
        #         | (Comment.text.ilike("% " + "@" + self.username + ",%"))
        #         | (Comment.text.ilike("%," + "@" + self.username + "."))
        #         | (Comment.text.ilike("%," + "@" + self.username + ",%"))
        #         | (Comment.text.ilike(self.username + "," + "%"))
        #         | (Comment.text.ilike("%" + "," + self.username))
        #         | (Comment.text.ilike("@" + self.username + "," + "%"))
        #         | (Comment.text.ilike("%" + "," + "@" + self.username))
        #         | (Comment.text.ilike("%," + self.username + " %"))
        #         | (Comment.text.ilike("%," + "@" + self.username + " %"))
        #         | (Comment.text.ilike("%>" + "@" + self.username + " %"))
        #         | (Comment.text.ilike("%>" + self.username + " %"))
        #     )
        mention = (
            current_user.new_mentions_view()
            .filter(Comment.date_to_publish > self.last_seen_mention)
            .all()
        )

        return mention

    def new_mentions_view(self):
        mention = Comment.query.filter(
            (Comment.text.ilike("% " + self.username + " %"))
            | (Comment.text.ilike("% " + "@" + self.username + " %"))
            | (Comment.text.ilike("@" + self.username))
            | (Comment.text.ilike(self.username))
            | (Comment.text.ilike("@" + self.username + " %"))
            | (Comment.text.ilike(self.username + " %"))
            | (Comment.text.ilike("% " + "@" + self.username))
            | (Comment.text.ilike("% " + self.username))
            | (Comment.text.ilike("%," + self.username))
            | (Comment.text.ilike("% " + self.username + ",%"))
            | (Comment.text.ilike("%," + self.username + "."))
            | (Comment.text.ilike("%," + self.username + ",%"))
            | (Comment.text.ilike("%," + "@" + self.username))
            | (Comment.text.ilike("% " + "@" + self.username + ",%"))
            | (Comment.text.ilike("%," + "@" + self.username + "."))
            | (Comment.text.ilike("%," + "@" + self.username + ",%"))
            | (Comment.text.ilike(self.username + "," + "%"))
            | (Comment.text.ilike("%" + "," + self.username))
            | (Comment.text.ilike("@" + self.username + "," + "%"))
            | (Comment.text.ilike("%" + "," + "@" + self.username))
            | (Comment.text.ilike("%," + self.username + " %"))
            | (Comment.text.ilike("%," + "@" + self.username + " %"))
            | (Comment.text.ilike("%>" + "@" + self.username + " %"))
            | (Comment.text.ilike("%>" + self.username + " %"))
        ).order_by(Comment.date_to_publish.desc())
        return mention


# Anonymous User Informations


class Anonymous(AnonymousUserMixin):
    def __init__(self):
        self.username = "Guest"
        self.id = "0"


# Posts database
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pin = db.Column(db.Integer, default=0)
    topic = db.Column(db.String(150), nullable=False)
    body = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.now)
    last_comment = db.Column(db.DateTime, default=datetime.now)
    date_to_publish = db.Column(db.DateTime, default=datetime.now)
    slug = db.Column(db.String(300), nullable=True)
    total_views = db.Column(db.Integer, default=0)
    author = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    category = db.Column(
        db.Integer,
        db.ForeignKey("postcategory.id", ondelete="SET NULL"),
        nullable=False,
    )
    # saved_comment = db.relationship('Save', backref='post',foreign_keys='Save.postid', passive_deletes=True)
    saved_post = db.relationship(
        "SavePost", backref="post", foreign_keys="SavePost.postid", passive_deletes=True
    )
    share = db.relationship("Shared", backref="post", passive_deletes=True)

    # post_comment = db.relationship("Comment", backref="post", passive_deletes=True)

    # This are the custom functions for the post class
    def i_have_liked(self):
        post_exists = Post.query.filter_by(id=self.id).first()
        return (
            True
            if (
                current_user.id in map(lambda x: x.user, post_exists.likepost)
                and post_exists.id in map(lambda x: x.postid, post_exists.likepost)
            )
            else False
        )

    def total_likes(self):
        post_exists = Post.query.filter_by(id=self.id).first()
        return len(post_exists.likepost)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    anon = db.Column(db.String(150), nullable=True)
    text = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.now)
    date_to_publish = db.Column(db.DateTime, default=datetime.now)
    author = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), default="Anonymous"
    )
    post = db.Column(
        db.Integer, db.ForeignKey("post.id", ondelete="CASCADE"), nullable=False
    )
    comment = db.relationship("Post", backref="comment", passive_deletes=True)
    # saved_comment = db.relationship('Save', backref='comment',foreign_keys='Save.commentid', passive_deletes=True)
    saved_post = db.relationship(
        "SavePost",
        backref="comment",
        foreign_keys="SavePost.commentid",
        passive_deletes=True,
    )
    # Comment = db.relationship('User', backref='comment', passive_deletes=True)
    share = db.relationship("Shared", backref="comment", passive_deletes=True)

    # This are the custom functions for the comment class
    def i_have_liked(self):
        comment_exists = Comment.query.filter_by(id=self.id).first()
        return (
            True
            if (
                current_user.id in map(lambda x: x.user, comment_exists.like)
                and comment_exists.id in map(lambda x: x.commentid, comment_exists.like)
            )
            else False
        )

    def total_likes(self):
        comment_exists = Comment.query.filter_by(id=self.id).first()
        return len(comment_exists.like)


class Postcategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True)
    mod = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    posts = db.relationship("Post", backref="postcategory", passive_deletes=True)


class Trending(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    slug = db.Column(db.String(200))
    date_created = db.Column(db.DateTime, default=datetime.now)
    date_to_publish = db.Column(db.DateTime, default=datetime.now)
    postid = db.Column(db.Integer, db.ForeignKey("post.id", ondelete="SET NULL"))
    trends = db.relationship("Post", backref="trending", passive_deletes=True)


class Save(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    date_created = db.Column(db.DateTime, default=datetime.now)
    date_to_publish = db.Column(db.DateTime, default=datetime.now)
    postid = db.Column(
        db.Integer, db.ForeignKey("post.id", ondelete="SET NULL"), nullable=False
    )
    commentid = db.Column(db.Integer, db.ForeignKey("comment.id", ondelete="SET NULL"))
    save = db.relationship("Post", backref="save", passive_deletes=True)
    save_comment = db.relationship("Comment", backref="save", passive_deletes=True)


class SavePost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    date_created = db.Column(db.DateTime, default=datetime.now)
    date_to_publish = db.Column(db.DateTime, default=datetime.now)
    postid = db.Column(
        db.Integer, db.ForeignKey("post.id", ondelete="SET NULL"), nullable=False
    )
    commentid = db.Column(db.Integer, db.ForeignKey("comment.id", ondelete="SET NULL"))
    # saveposts = db.relationship('Post', backref='savepost', passive_deletes=True, uselist=True)
    # save_comment = db.relationship('Comment', backref='savepost', passive_deletes=True,overlaps="comment,saved_post")


class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    date_created = db.Column(db.DateTime, default=datetime.now)
    postid = db.Column(
        db.Integer, db.ForeignKey("post.id", ondelete="SET NULL"), nullable=False
    )
    commentid = db.Column(db.Integer, db.ForeignKey("comment.id", ondelete="SET NULL"))
    like = db.relationship("Post", backref="like", passive_deletes=True)
    like_comment = db.relationship("Comment", backref="like", passive_deletes=True)


class LikePost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    date_created = db.Column(db.DateTime, default=datetime.now)
    postid = db.Column(
        db.Integer, db.ForeignKey("post.id", ondelete="SET NULL"), nullable=False
    )
    commentid = db.Column(db.Integer, db.ForeignKey("comment.id", ondelete="SET NULL"))
    like = db.relationship("Post", backref="likepost", passive_deletes=True)
    like_comment = db.relationship("Comment", backref="likepost", passive_deletes=True)


class Shared(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    date_created = db.Column(db.DateTime, default=datetime.now)
    date_to_publish = db.Column(db.DateTime, default=datetime.now)
    postid = db.Column(
        db.Integer, db.ForeignKey("post.id", ondelete="SET NULL"), nullable=False
    )
    commentid = db.Column(db.Integer, db.ForeignKey("comment.id", ondelete="SET NULL"))
    # shares = db.relationship('Post', backref='shared', passive_deletes=True)
    # cshares = db.relationship('Comment', backref='shared',overlaps="comment,share", passive_deletes=True)


# class Shared(db.Model):
#     id = db.Column(db.Integer,primary_key=True)
#     user = db.Column(db.Integer,db.ForeignKey('user.id', ondelete='SET NULL'))
#     date_created = db.Column(db.DateTime, default= datetime.now)
#     date_to_publish = db.Column(db.DateTime, default= datetime.now)
#     postid = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='SET NULL'),nullable= False)
#     commentid = db.Column(db.Integer, db.ForeignKey('comment.id', ondelete='SET NULL'))
#     cshares = db.relationship('Comment', backref='shared', passive_deletes=True)
