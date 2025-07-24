import uuid

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

User = get_user_model()


class Unit(models.Model):
    name = models.CharField(max_length=30, verbose_name='Название')

    class Meta:
        ordering = ['name']
        verbose_name = 'единица измерения'
        verbose_name_plural = 'Единицы измерения'

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=64, verbose_name='Название')
    slug = models.SlugField(
        max_length=64,
        unique=True,
        verbose_name='Слаг',
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=40)
    measurement_unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name='ingredients',
        verbose_name='Единица измерения'
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return f'{self.name} ({self.measurement_unit.name})'


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    name = models.CharField(max_length=256,verbose_name='Название')
    image = models.ImageField(upload_to='recipes', verbose_name='Изображение')
    text = models.TextField(verbose_name='Описание')
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Тег'
    )
    cooking_time = models.IntegerField(validators=[MinValueValidator(1)], verbose_name='Время приготовления')
    short_code = models.CharField(max_length=8, unique=True, blank=True, verbose_name='Код для ссылки')

    class Meta:
        ordering = ['id']
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'

    def save(self, *args, **kwargs):
        if not self.short_code:
            self.short_code = str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name[:30]


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredients',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.PROTECT,
        related_name='used_in',
        verbose_name='Ингредиент',
    )
    amount = models.IntegerField(verbose_name='Количество')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name='unique_ingredient',
                fields=['recipe', 'ingredient'],
            ),
        ]
        verbose_name = 'рецепт и ингредиенты'
        verbose_name_plural = 'Рецепты и ингредиенты'

    def __str__(self):
        return f'{self.ingredient.name[:30]}: {self.amount}'


class ShoppingCart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shopping_cart', verbose_name='Пользователь')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='shopping_cart', verbose_name='Рецепт')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'recipe'], name='unique_shopping_cart')
        ]
        verbose_name = 'список покупок'
        verbose_name_plural = 'Список покупок'

    def __str__(self):
        return f'{self.user.username}: {self.recipe.name}'


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites', verbose_name='Пользователь')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='favorites', verbose_name='Рецепт')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'recipe'], name='unique_favorite')
        ]
        verbose_name = 'избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'

    def __str__(self):
        return f'{self.user.username}: {self.recipe.name}'