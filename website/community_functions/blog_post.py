import feedparser as fp


class Blogpost:
    def __init__(self):
        self.url = "http://www.reddit.com/r/python/.rss"

    def feed(self, url):
        url = self.url
        d = fp.parse(url)
        print(d["entries"][0]["title"], d["entries"][0]["description"])

        # user_post = Post(
        #                     topic=string.capwords(topic),
        #                     body=body,
        #                     category=category,
        #                     author=current_user.id,
        #                     slug=slugify(slug),
        #                 )
        return url
