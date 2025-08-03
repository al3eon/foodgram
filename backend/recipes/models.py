import uuid

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Exists, OuterRef, BooleanField, Value, Manager

from .constants import (
    INGREDIENT_NAME_MAX_LENGTH, NAME_STR_LIMIT, RECIPE_NAME_MAX_LENGTH,
    SHORT_CODE_MAX_LENGTH, TAG_NAME_MAX_LENGTH,
    TAG_SLUG_MAX_LENGTH, UNIT_NAME_MAX_LENGTH,
)

User = get_user_model()


class Unit(models.Model):
    name = models.CharField(
        max_length=UNIT_NAME_MAX_LENGTH,
        verbose_name='Название'
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'единица измерения'
        verbose_name_plural = 'Единицы измерения'

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(
        max_length=TAG_NAME_MAX_LENGTH,
        unique=True,
        verbose_name='Название'
    )
    slug = models.SlugField(
        max_length=TAG_SLUG_MAX_LENGTH,
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
    name = models.CharField(
        max_length=INGREDIENT_NAME_MAX_LENGTH,
        verbose_name='Название'
    )
    measurement_unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name='ingredients',
        verbose_name='Единица измерения',
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'

        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient_unit',
            )
        ]

    def __str__(self):
        return f'{self.name} ({self.measurement_unit.name})'


class RecipeManager(Manager):
    def with_user_annotations(self, user):
        """Добавляет аннотации is_favorited и is_in_shopping_cart к queryset."""
        if user.is_authenticated:
            return self.get_queryset().annotate(
                is_favorited=Exists(
                    Favorite.objects.filter(user=user, recipe=OuterRef('pk'))
                ),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(user=user, recipe=OuterRef('pk'))
                )
            )
        return self.get_queryset().annotate(
            is_favorited=Value(False, output_field=BooleanField()),
            is_in_shopping_cart=Value(False, output_field=BooleanField())
        )


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    name = models.CharField(
        max_length=RECIPE_NAME_MAX_LENGTH,
        verbose_name='Название'
    )
    image = models.ImageField(
        upload_to='recipes',
        blank=False,
        null=False,
        verbose_name='Изображение'
    )
    text = models.TextField(verbose_name='Описание')
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Тег'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name='Ингредиенты'
    )
    cooking_time = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Время приготовления'
    )
    short_code = models.CharField(
        max_length=SHORT_CODE_MAX_LENGTH,
        unique=True,
        blank=True,
        verbose_name='Код для ссылки'
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата публикации'
    )

    objects = RecipeManager()

    class Meta:
        ordering = ['-pub_date']
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'

    def save(self, *args, **kwargs):
        if not self.short_code:
            while True:
                short_code = str(uuid.uuid4())[:SHORT_CODE_MAX_LENGTH]
                if not Recipe.objects.filter(short_code=short_code).exists():
                    self.short_code = short_code
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name[:NAME_STR_LIMIT]


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredient_relations',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.PROTECT,
        related_name='used_in',
        verbose_name='Ингредиент',
    )
    amount = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Количество'
    )

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
        return f'{self.ingredient.name[:NAME_STR_LIMIT]}: {self.amount}'


class BaseUserRecipeModel(models.Model):
    """Абстрактная модель для ShoppingCart и Favorite."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='%(model_name)s',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        'Recipe',
        on_delete=models.CASCADE,
        related_name='%(model_name)s',
        verbose_name='Рецепт'
    )

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='%(app_label)s_%(class)s_unique'
            )
        ]


class ShoppingCart(BaseUserRecipeModel):
    class Meta(BaseUserRecipeModel.Meta):
        verbose_name = 'список покупок'
        verbose_name_plural = 'Список покупок'

    def __str__(self):
        return f'{self.user.username}: {self.recipe.name}'


class Favorite(BaseUserRecipeModel):
    class Meta(BaseUserRecipeModel.Meta):
        verbose_name = 'избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'

    def __str__(self):
        return f'{self.user.username}: {self.recipe.name}'
