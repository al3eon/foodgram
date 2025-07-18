from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Units(models.Model):
    name = models.CharField(max_length=30)


class Tag(models.Model):
    name = models.CharField(max_length=64)


class Ingredient(models.Model):
    name = models.CharField(max_length=40)
    units = models.ForeignKey(Units, on_delete=models.CASCADE)


class Recipe(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    image = models.ImageField(upload_to='recipes')
    text = models.TextField()
    tags = models.ManyToManyField(Tag, through='RecipeTag')
    time = models.IntegerField()


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    count = models.IntegerField()
