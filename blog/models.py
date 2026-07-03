from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Blog(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(help_text="Short description for meta + card snippet")
    content = models.TextField(blank=True, default="", help_text="Full post body content")
    img_url = models.URLField(max_length=500, blank=True, default="")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="blogs")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blogs")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.APPROVED, db_index=True
    )
    published_at = models.DateTimeField(null=True, blank=True)
    meta_title = models.CharField(max_length=70, blank=True, default="", help_text="Custom SEO title (overrides post title)")
    meta_description = models.CharField(max_length=165, blank=True, default="", help_text="Custom meta description (overrides description field)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            counter = 1
            while Blog.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug

        if self.status == self.Status.APPROVED and not self.published_at:
            self.published_at = timezone.now()

        self.is_published = self.status == self.Status.APPROVED
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Comment(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blog_comments")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.user.username} on {self.blog.title}"


class Like(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blog_likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["blog", "user"]

    def __str__(self):
        return f"{self.user.username} likes {self.blog.title}"
