from django import forms
from .models import Blog, Category


class BlogForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = ["title", "description", "content", "img_url", "category", "status", "meta_title", "meta_description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "content": forms.Textarea(attrs={"rows": 15}),
        }


class CommentForm(forms.Form):
    body = forms.CharField(widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Share your thoughts..."}))
