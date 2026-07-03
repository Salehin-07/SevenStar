from django.urls import path
from . import views

app_name = "blog"

urlpatterns = [
    path("", views.blog_list, name="blog_list"),
    path("create/", views.blog_create, name="blog_create"),
    path("<slug:category_slug>/<slug:blog_slug>/", views.blog_detail, name="blog_detail"),
    path("<slug:category_slug>/<slug:blog_slug>/like/", views.blog_like, name="blog_like"),
]
