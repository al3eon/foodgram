from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Units(models.Model):
    name = models.CharField(max_length=30)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=40)
    units = models.ForeignKey(
        Units,
        on_delete=models.PROTECT,
        related_name='ingredients'
    )

    def __str__(self):
        return f'{self.name} ({self.units})'



class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes'
    )
    name = models.CharField(max_length=70)
    image = models.ImageField(upload_to='recipes')
    text = models.TextField()
    tags = models.ManyToManyField(
        Tag,
        through='RecipeTag',
        related_name='recipes'
    )
    time = models.IntegerField()

    def __str__(self):
        return self.name[:30]


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredients')
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.PROTECT,
        related_name='used_in'
    )
    count = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name='unique_ingredient',
                fields=['recipe', 'ingredient'],
            ),
        ]
    def __str__(self):
        return f'{self.ingredient.name[:30]}: {self.count}'
