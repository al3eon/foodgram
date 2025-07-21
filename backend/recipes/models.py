from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

User = get_user_model()


class Units(models.Model):
    name = models.CharField(max_length=30)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=64)
    slug = models.SlugField(
        max_length=64,
        unique=True,
        verbose_name='Слаг',
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=40)
    measurement_unit = models.ForeignKey(
        Units,
        on_delete=models.PROTECT,
        related_name='ingredients'
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.units})'


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes'
    )
    name = models.CharField(max_length=256)
    image = models.ImageField(upload_to='recipes')
    text = models.TextField()
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes'
    )
    cooking_time = models.IntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ['name']

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
    amount = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name='unique_ingredient',
                fields=['recipe', 'ingredient'],
            ),
        ]

    def __str__(self):
        return f'{self.ingredient.name[:30]}: {self.amount}'


class ShoppingCart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shopping_cart')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='shopping_cart')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'recipe'], name='unique_shopping_cart')
        ]

    def __str__(self):
        return f'{self.user.username}: {self.recipe.name}'


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='favorites')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'recipe'], name='unique_favorite')
        ]

    def __str__(self):
        return f'{self.user.username}: {self.recipe.name}'