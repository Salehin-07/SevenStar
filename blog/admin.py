from django.contrib import admin
from .models import Category, Blog, Comment, Like


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "slug")
    search_fields = ("name",)


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ("user", "body", "created_at")


class LikeInline(admin.TabularInline):
    model = Like
    extra = 0
    readonly_fields = ("user", "created_at")


@admin.action(description="Approve selected posts")
def approve_posts(modeladmin, request, queryset):
    from django.utils import timezone
    updated = queryset.update(status=Blog.Status.APPROVED, published_at=timezone.now(), is_published=True)
    modeladmin.message_user(request, f"{updated} post(s) approved.")


@admin.action(description="Reject selected posts")
def reject_posts(modeladmin, request, queryset):
    updated = queryset.update(status=Blog.Status.REJECTED, is_published=False)
    modeladmin.message_user(request, f"{updated} post(s) rejected.")


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    list_display = ("title", "category", "author", "status", "published_at", "created_at")
    list_filter = ("category", "status", "created_at")
    search_fields = ("title", "description", "content")
    readonly_fields = ("author", "published_at", "is_published")
    actions = [approve_posts, reject_posts]
    inlines = [CommentInline, LikeInline]
    fieldsets = (
        (None, {
            "fields": ("title", "slug", "description", "content", "img_url", "category", "author")
        }),
        ("Status", {
            "fields": ("status", "published_at", "is_published"),
        }),
        ("SEO", {
            "fields": ("meta_title", "meta_description"),
            "classes": ("collapse",),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("blog", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("body",)


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("blog", "user", "created_at")
