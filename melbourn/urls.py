"""
URL configuration for melbourn project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.views.generic import TemplateView

from .sitemaps import StaticViewSitemap, BlogSitemap
from blog.feeds import LatestBlogFeed

sitemaps = {
    "static": StaticViewSitemap,
    "blog": BlogSitemap,
}

urlpatterns = [
    path('', include('core.urls')),
    path('', include('pwa.urls')),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    path('llms.txt', TemplateView.as_view(template_name='llms.txt', content_type='text/plain')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('feed/', LatestBlogFeed(), name='feed'),
    path('accounts/', include('accounts.urls')),
    path('X7N9bV2yP8uR5dL6qQyH3zT4cQ1dA0hE4gT6oF3bV9mN2pU8sA7dWqQyH3zT4c1-admin/', admin.site.urls),
    path('book-now/', include('orders.urls')),
    path('book-tours/', include('tours.urls')),
    path('blog/', include('blog.urls')),
]
