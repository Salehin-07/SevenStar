from django.contrib.syndication.views import Feed
from django.urls import reverse
from .models import Blog


class LatestBlogFeed(Feed):
    title = "SevenStar Limo & Chauffeur — Blog"
    link = "/blog/"
    description = "Latest news, tips and guides from Melbourne's premier chauffeur service."

    def items(self):
        return Blog.objects.filter(status=Blog.Status.APPROVED)[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description

    def item_pubdate(self, item):
        return item.published_at

    def item_link(self, item):
        return reverse("blog:blog_detail", args=[item.category.slug, item.slug])
