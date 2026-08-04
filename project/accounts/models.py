from django.db import models
from model.base import BaseDatabaseModel
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    bio = models.TextField(max_length=500, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True)
    password_change_count = models.PositiveSmallIntegerField(default=0)
    password_change_date = models.DateField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
    
# class User(AbstractUser,BaseDatabaseModel):
#     email = models.EmailField(unique=True)
#     bio = models.TextField(max_length=500, blank=True)
#     phone_number = models.CharField(max_length=15, blank=True)
#     profile_picture = models.ImageField(upload_to='profile_pics/', blank=True)

#     password_change_count = models.PositiveSmallIntegerField(default=0)
#     password_change_date = models.DateField(null=True, blank=True)

#     USERNAME_FIELD = 'email'
#     REQUIRED_FIELDS = ['username']

#     def __str__(self):
#         return self.email
