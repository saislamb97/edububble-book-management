from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db.models.signals import post_save
from django.dispatch import receiver
import random

def generate_unique_id():
    # Generate a random 6-digit unique ID
    unique_id = random.randint(100000, 999999)
    return unique_id

class CustomAccountManager(BaseUserManager):

    def create_superuser(self, email, username, password, **other_fields):
        if not email:
            raise ValueError('You must provide an email address')

        email = self.normalize_email(email)
        
        # Create the user instance
        user = self.model(email=email, username=username, **other_fields)
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        return user
    
    def create_user(self, email, username, password, **other_fields):
        if not email:
            raise ValueError('You must provide an email address')

        email = self.normalize_email(email)
        
        # Create the user instance
        user = self.model(email=email, username=username, **other_fields)
        user.set_password(password)
        user.save()
        return user


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=250, unique=True)
    username = models.CharField(max_length=250, unique=True)
    fullname = models.CharField(max_length=250, blank=True)
    start_date = models.DateTimeField(default=timezone.now)
    is_student = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = CustomAccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username',]

    def __str__(self):
        return self.username
            
    def save(self, *args, **kwargs):
        if sum([self.is_student, self.is_staff]) > 1:
            raise ValidationError("A user cannot have multiple roles simultaneously.")
        super().save(*args, **kwargs)

class ClassName(models.Model):
    CLASS_CHOICES = [
        ('Form1', 'Form1'),
        ('Form2', 'Form2'),
        ('Form3', 'Form3'),
        ('Form4', 'Form4'),
        ('Form5', 'Form5'),
    ]
    classname = models.CharField(max_length=250, choices=CLASS_CHOICES, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.classname
    
class Textbooks(models.Model):
    book_title = models.CharField(max_length=250)
    book_id = models.CharField(max_length=250, default=generate_unique_id, unique=True)
    classname = models.ForeignKey(ClassName, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return self.book_title

class Students(models.Model):
    username = models.ForeignKey(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=250, default=generate_unique_id, unique=True)
    classname = models.ForeignKey(ClassName, on_delete=models.SET_NULL, null=True)
    SECTION_CHOICES = [
        ('EXA', 'EXA'),
        ('PETA', 'PETA'),
        ('TERA', 'TERA'),
        ('GIGA', 'GIG'),
        ('MEGA', 'MEGA'),
    ]
    section = models.CharField(max_length=250, blank=True, null=True, choices=SECTION_CHOICES)
    textbooks = models.ManyToManyField(Textbooks, blank=True)

    def __str__(self):
        return f"{self.username} - {self.student_id} - {self.classname}"
    
class TextbookStatus(models.Model):
    student = models.ForeignKey(Students, on_delete=models.CASCADE)
    textbook = models.ForeignKey(Textbooks, on_delete=models.CASCADE)
    collected = models.BooleanField(default=False)
    returned = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if sum([self.collected, self.returned]) > 1:
            raise ValidationError("Only one status can be selected.")
        super().save(*args, **kwargs)
    
@receiver(post_save, sender=User)
def create_or_update_student_profile(sender, instance, created, **kwargs):
    if instance.is_student:
        if created:
            Students.objects.create(username=instance)
        else:
            student_profile, _ = Students.objects.get_or_create(username=instance)
            student_profile.save()
    else:
        Students.objects.filter(username=instance).delete()

@receiver(post_save, sender=User)
def delete_student_profile(sender, instance, **kwargs):
    if not instance.is_student:
        Students.objects.filter(username=instance).delete()