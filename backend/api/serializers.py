import os

from django.contrib.auth import get_user_model
from django.db.transaction import atomic
from djoser.serializers import (SetPasswordSerializer, UserCreateSerializer,
                                UserSerializer)
from drf_extra_fields.fields import Base64ImageField
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from rest_framework import serializers
from users.models import Subscription

User = get_user_model()


class IsSubscribedMixin:
    """Миксин для добавления поля is_subscribed."""
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    def get_is_subscribed(self, obj):
        """Проверяет, подписан ли текущий пользователь на объект."""
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return Subscription.objects.filter(
            user=request.user, author=obj).exists()


class CustomUserCreateSerializer(UserCreateSerializer):
    """Сериализатор для создания пользователя."""
    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password'
        )
        extra_kwargs = {'password': {'write_only': True}}


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для краткого представления рецепта."""
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class UserListSerializer(IsSubscribedMixin, serializers.ModelSerializer):
    """Сериализатор для списка пользователей."""
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'avatar')


class CustomUserSerializer(IsSubscribedMixin, UserSerializer):
    """Сериализатор для детального представления пользователя."""
    is_subscribed = serializers.SerializerMethodField(read_only=True)
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta(UserSerializer.Meta):
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar'
        )


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для аватара."""
    avatar = Base64ImageField(write_only=True, required=False, allow_null=True)
    avatar_input = serializers.ImageField(
        write_only=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('avatar', 'avatar_input')

    def validate_avatar_input(self, value):
        if not value:
            raise serializers.ValidationError('Файл отсутствует.')
        valid_extensions = ['.png', '.jpg', '.jpeg']
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in valid_extensions:
            raise serializers.ValidationError('Неподдерживаемый формат. '
                                              'Используйте PNG или JPEG')
        return value

    def update(self, instance, validated_data):
        if 'avatar_input' in validated_data and validated_data['avatar_input']:
            instance.avatar = validated_data['avatar_input']
            instance.save()
        return instance


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

    def validate(self,data):
        """Проверяет наличие и уникальность тегов и ингредиентов."""
        if not data.get('image'):
            raise serializers.ValidationError({'image': 'Поле image не может быть пустым'})

        tags = data.get('tags')
        ingredients = data.get('ingredients')

        if not tags:
            raise serializers.ValidationError({'tags': 'Нужен хотя бы один тег'})
        tag_ids = [tag.id for tag in tags]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError({'tags': 'Теги не должны повторяться'})

        if not ingredients:
            raise serializers.ValidationError({'ingredients': 'Нужен хотя бы один ингредиент'})
        seen = set()
        for item in ingredients:
            if item['ingredient'] in seen:
                raise serializers.ValidationError(
                    {'ingredients': 'Ингредиенты не должны повторяться'}
                )
            seen.add(item['ingredient'])

        return data

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
        if tags is not None:
            instance.tags.set(tags)
        if ingredients is not None:
            instance.ingredients.clear()
            self.create_ingredients(instance, ingredients)
        return super().update(instance, validated_data)


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения ингредиентов в рецепте."""
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit.name')
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецептов."""
    tags = TagSerializer(many=True, read_only=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        source='ingredient_relations',many=True, read_only=True)
    image = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'author', 'name', 'image', 'text',
                  'tags', 'ingredients', 'cooking_time',
                  'is_in_shopping_cart', 'is_favorited')

    def get_image(self, obj):
        return obj.image.url if obj.image else ""

    def get_is_in_shopping_cart(self, obj):
        """Проверяет, добавлен ли рецепт в корзину покупок."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ShoppingCart.objects.filter(
                user=request.user, recipe=obj).exists()
        return False

    def get_is_favorited(self, obj):
        """Проверяет, добавлен ли рецепт в избранное."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(
                user=request.user, recipe=obj).exists()
        return False


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""
    measurement_unit = serializers.CharField(source='measurement_unit.name')

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeRelationSerializer(serializers.ModelSerializer):
    """Сериализатор для представления рецепта в корзине или избранном."""
    id = serializers.IntegerField(source='recipe.id')
    name = serializers.CharField(source='recipe.name')
    image = serializers.ImageField(source='recipe.image')
    cooking_time = serializers.IntegerField(source='recipe.cooking_time')

    class Meta:
        fields = ('id', 'name', 'image', 'cooking_time')


class ShoppingCartSerializer(RecipeRelationSerializer):
    """Сериализатор для корзины покупок."""
    class Meta(RecipeRelationSerializer.Meta):
        model = ShoppingCart


class FavoriteSerializer(RecipeRelationSerializer):
    """Сериализатор для избранных рецептов."""
    class Meta(RecipeRelationSerializer.Meta):
        model = Favorite


class CustomSetPasswordSerializer(SetPasswordSerializer):
    """Сериализатор для смены пароля пользователя."""
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class SubscriptionSerializer(CustomUserSerializer):
    """Сериализатор для подписок пользователя."""
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(CustomUserSerializer.Meta):
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
