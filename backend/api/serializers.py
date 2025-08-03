from django.contrib.auth import get_user_model
from django.db.transaction import atomic
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import (Ingredient, Recipe, RecipeIngredient, Tag)
from users.models import Subscription

User = get_user_model()


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для краткого представления рецепта."""
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class ProfileSerializer(serializers.ModelSerializer):
    """Сериализатор для детального представления пользователя."""
    is_subscribed = serializers.SerializerMethodField(read_only=True)
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, obj):
        """Проверяет, подписан ли текущий пользователь на объект."""
        request = self.context.get('request')
        return (request is not None
                and request.user.is_authenticated
                and obj is not None
                and Subscription.objects.filter(
                    user=request.user, author=obj).exists())


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для аватара."""
    avatar = Base64ImageField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('avatar',)

    def validate(self, attrs):
        if 'avatar' not in attrs or attrs.get('avatar') in [None, '']:
            raise serializers.ValidationError({
                'avatar': 'Это поле обязательно для обновления аватара.'
            })
        return attrs


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class RecipeIngredientWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для записи ингредиентов в рецепте."""
    id = serializers.PrimaryKeyRelatedField(source='ingredient',
                                            queryset=Ingredient.objects.all())

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов."""
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=True)
    ingredients = RecipeIngredientWriteSerializer(many=True, required=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('name', 'text', 'tags',
                  'ingredients', 'image', 'cooking_time')

    def validate(self, data):
        """Проверяет наличие и уникальность тегов и ингредиентов."""
        tags = data.get('tags')
        ingredients = data.get('ingredients')

        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Нужен хотя бы один тег'})
        tag_ids = [tag.id for tag in tags]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError(
                {'tags': 'Теги не должны повторяться'})

        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': 'Нужен хотя бы один ингредиент'})
        seen = set()
        for item in ingredients:
            if item['ingredient'] in seen:
                raise serializers.ValidationError(
                    {'ingredients': 'Ингредиенты не должны повторяться'}
                )
            seen.add(item['ingredient'])

        return data

    def validate_image(self, value):
        """Проверяет наличие изображения"""
        if not value:
            raise serializers.ValidationError(
                {'image': 'Поле image не может быть пустым'})
        return value

    def create_ingredients(self, recipe, ingredients):
        """Создает связи ингредиентов с рецептом."""
        objs = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient_data['ingredient'],
                amount=ingredient_data['amount']
            )
            for ingredient_data in ingredients
        ]
        RecipeIngredient.objects.bulk_create(objs)

    @atomic
    def create(self, validated_data):
        """Создает новый рецепт."""
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        validated_data['author'] = self.context['request'].user
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients(recipe, ingredients)
        return recipe

    @atomic
    def update(self, instance, validated_data):
        """Обновляет существующий рецепт."""
        tags = validated_data.pop('tags', None)
        ingredients = validated_data.pop('ingredients', None)
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.create_ingredients(instance, ingredients)
        validated_data['author'] = self.context['request'].user
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        """Возвращает данные рецепта в формате RecipeReadSerializer."""
        user = self.context['request'].user
        annotated_recipe = Recipe.objects.with_user_annotations(
            user).get(pk=instance.pk)
        return RecipeReadSerializer(
            annotated_recipe, context=self.context).data


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения ингредиентов в рецепте."""
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit.name')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецептов."""
    tags = TagSerializer(many=True, read_only=True)
    author = ProfileSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        source='ingredient_relations', many=True, read_only=True)
    image = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(
        read_only=True, default=False)
    is_favorited = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = Recipe
        fields = ('id', 'author', 'name', 'image', 'text',
                  'tags', 'ingredients', 'cooking_time',
                  'is_in_shopping_cart', 'is_favorited')

    def get_image(self, obj):
        return obj.image.url if obj.image else ""


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""
    measurement_unit = serializers.CharField(source='measurement_unit.name')

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class SubscriptionSerializer(ProfileSerializer):
    """Сериализатор для подписок пользователя."""
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(ProfileSerializer.Meta):
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar', 'recipes', 'recipes_count'
        )

    def get_recipes(self, obj):
        """Возвращает рецепты пользователя с учетом лимита."""
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit')
        recipes = obj.recipes.all()
        if recipes_limit:
            try:
                recipes = recipes[:int(recipes_limit)]
            except ValueError:
                pass
        return ShortRecipeSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        """Возвращает количество рецептов пользователя."""
        return obj.recipes.count()
