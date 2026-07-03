from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from blog.models import Blog


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = "monthly"

    def items(self):
        return [
            "home",
            "about",
            "contact",
            "terms",
            "privacy_policy",
            "orders",
            "tours",
            "blog:blog_list",
        ]

    def location(self, item):
        return reverse(item)


class BlogSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Blog.objects.filter(status=Blog.Status.APPROVED)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        from django.urls import reverse
        return reverse("blog:blog_detail", args=[obj.category.slug, obj.slug])
