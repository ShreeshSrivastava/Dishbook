from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Recipe(models.Model):
    title = models.CharField(max_length=200)
    photo = models.ImageField(upload_to="media/", null=True, blank=True)
    description = models.TextField()
    prep_time_minutes = models.IntegerField()
    cook_time_minutes = models.IntegerField()
    serves = models.IntegerField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    copied_from = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name="copies")
    featured_on = models.DateField(null=True, blank=True)
    tags = models.ManyToManyField('Tag', blank=True)

class Step(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='steps')
    order = models.IntegerField()
    description = models.TextField()

class Ingredient(models.Model):
    step = models.ForeignKey(Step, on_delete=models.CASCADE, related_name='ingredients')
    amount = models.CharField(max_length=50)
    unit = models.CharField(max_length=50)
    name = models.CharField(max_length=100)

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to="media/", null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
