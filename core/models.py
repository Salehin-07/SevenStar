from django.db import models

# Create your models here.
class Contact(models.Model):
    phone = models.CharField(max_length=30)
    email = models.EmailField(max_length=254)
    location = models.CharField(max_length=200)
    opening_hours_week = models.CharField(max_length=200)
    abn = models.CharField(max_length=50)
    bank_details = models.TextField(blank=True, default="", help_text="Bank account details sent in payment emails")
    
    def __str__(self):
        return "Contact Information"

class ContactRequest(models.Model):
    email = models.EmailField(max_length=254)
    what_said = models.TextField()
    
    def __str__(self):
        return self.email

class FAQ(models.Model):
    question = models.CharField(max_length=256)
    answer = models.TextField()
    
    def __str__(self):
        return self.question