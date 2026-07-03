from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count
from .models import Blog, Category, Comment, Like
from .forms import BlogForm, CommentForm


def blog_list(request):
    blogs = Blog.objects.filter(status=Blog.Status.APPROVED).select_related("category", "author").annotate(
        like_count=Count("likes"), comment_count=Count("comments")
    ).order_by('-published_at', '-created_at')
    categories = Category.objects.all()
    selected_category = request.GET.get("category")

    if selected_category:
        blogs = blogs.filter(category__slug=selected_category)

    paginator = Paginator(blogs, 9)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "blog/blog_list.html", {
        "page_obj": page_obj,
        "categories": categories,
        "selected_category": selected_category,
    })


def blog_detail(request, category_slug, blog_slug):
    blog = get_object_or_404(
        Blog.objects.select_related("category", "author").annotate(
            like_count=Count("likes"), comment_count=Count("comments")
        ),
        slug=blog_slug,
        category__slug=category_slug,
        status=Blog.Status.APPROVED,
    )
    comments = blog.comments.select_related("user").all()
    user_liked = False
    if request.user.is_authenticated:
        user_liked = blog.likes.filter(user=request.user).exists()

    if request.method == "POST" and request.user.is_authenticated:
        form = CommentForm(request.POST)
        if form.is_valid():
            Comment.objects.create(
                blog=blog,
                user=request.user,
                body=form.cleaned_data["body"],
            )
            messages.success(request, "Your comment has been posted.")
            return redirect("blog:blog_detail", category_slug=category_slug, blog_slug=blog_slug)
    else:
        form = CommentForm()

    # Get related blogs in same category
    related_blogs = Blog.objects.filter(
        category=blog.category, status=Blog.Status.APPROVED
    ).exclude(pk=blog.pk).order_by('-published_at', '-created_at')[:3]

    return render(request, "blog/blog_detail.html", {
        "blog": blog,
        "comments": comments,
        "form": form,
        "user_liked": user_liked,
        "related_blogs": related_blogs,
    })


@login_required
def blog_like(request, category_slug, blog_slug):
    blog = get_object_or_404(Blog, slug=blog_slug, category__slug=category_slug)
    like, created = Like.objects.get_or_create(blog=blog, user=request.user)
    if not created:
        like.delete()
    return redirect("blog:blog_detail", category_slug=category_slug, blog_slug=blog_slug)


@user_passes_test(lambda u: u.is_superuser)
def blog_create(request):
    if request.method == "POST":
        form = BlogForm(request.POST)
        if form.is_valid():
            blog = form.save(commit=False)
            blog.author = request.user
            blog.save()
            messages.success(request, "Blog post created successfully!")
            return redirect("blog:blog_detail", category_slug=blog.category.slug, blog_slug=blog.slug)
    else:
        form = BlogForm()
    return render(request, "blog/blog_create.html", {"form": form})
