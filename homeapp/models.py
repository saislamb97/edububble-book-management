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
    email = models.EmailField(max_length=250, unique=True, blank=True)
    username = models.CharField(max_length=250, unique=True)
    fullname = models.CharField(max_length=250)
    start_date = models.DateTimeField(default=timezone.now)
    is_student = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = CustomAccountManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        if not self.email:
            self.email = f"{self.username}@example.com"

        if not self.fullname:
            self.fullname = self.username

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
        ('Graduate', 'Graduate'),
    ]
    classname = models.CharField(max_length=250, choices=CLASS_CHOICES, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.classname
    
class Textbook(models.Model):
    book_title = models.CharField(max_length=250)
    book_id = models.CharField(max_length=250, default=generate_unique_id, unique=True)
    classname = models.ForeignKey(ClassName, on_delete=models.SET_NULL, null=True)
    quantity_total = models.IntegerField(null=True, blank=True, default=100)
    available_quantity = models.IntegerField(null=True, blank=True, default=100)
    
    def __str__(self):
        return f'{self.book_title} - {self.classname}'

class Student(models.Model):
    username = models.ForeignKey(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=250, default=generate_unique_id, unique=True)
    classname = models.ForeignKey(ClassName, on_delete=models.SET_NULL, null=True)
    SECTION_CHOICES = [
        ('EXA', 'EXA'),
        ('PETA', 'PETA'),
        ('TERA', 'TERA'),
        ('GIGA', 'GIGA'),
        ('MEGA', 'MEGA'),
    ]
    section = models.CharField(max_length=250, blank=True, null=True, choices=SECTION_CHOICES)
    textbooks = models.ManyToManyField(Textbook, blank=True)

    def __str__(self):
        return f"{self.student_id} - {self.username.fullname} - {self.classname}"
    
class TextbookStatus(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    textbook = models.ForeignKey(Textbook, on_delete=models.CASCADE)
    collected = models.BooleanField(default=False)
    returned = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if sum([self.collected, self.returned]) > 1:
            raise ValidationError("Only one status can be selected.")
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Textbook Status"
        verbose_name_plural = "Textbook Statuses"

@receiver(post_save, sender=TextbookStatus)
def update_available_quantity(sender, instance, **kwargs):
    if instance.textbook.quantity_total is not None and instance.textbook.available_quantity is not None:
        # Calculate the total collected and returned for a specific textbook
        total_collected = TextbookStatus.objects.filter(textbook=instance.textbook, collected=True).count()

        # Calculate available quantity, ensuring it doesn't go below zero
        available_quantity = instance.textbook.quantity_total - total_collected
        instance.textbook.available_quantity = max(available_quantity, 0)
        instance.textbook.save()

@receiver(post_save, sender=Student)
def create_or_update_textbook_status(sender, instance, created, **kwargs):
    if created:
        # If a new Student is created, create a TextbookStatus for each associated textbook
        for textbook in instance.textbooks.all():
            TextbookStatus.objects.create(student=instance, textbook=textbook)
    else:
        # If an existing Student is updated, update TextbookStatus for each associated textbook
        for textbook in instance.textbooks.all():
            textbook_status, created = TextbookStatus.objects.get_or_create(student=instance, textbook=textbook)
        
@receiver(post_save, sender=User)
def create_or_update_student_profile(sender, instance, created, **kwargs):
    if instance.is_student:
        if created:
            student_profile = Student.objects.create(username=instance, student_id=instance.username)
        else:
            student_profile, _ = Student.objects.get_or_create(username=instance)
            student_profile.student_id = instance.username
            student_profile.save()
        
        # Update student profile with all textbooks
        all_textbooks = Textbook.objects.all()
        student_profile.textbooks.add(*all_textbooks)
    else:
        Student.objects.filter(username=instance).delete()

@receiver(post_save, sender=User)
def delete_student_profile(sender, instance, **kwargs):
    if not instance.is_student:
        Student.objects.filter(username=instance).delete()