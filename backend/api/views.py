import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models import Exists, OuterRef, Value
from django.db.models.fields import BooleanField
from django.http import HttpResponse, HttpResponseRedirect
from django.views import View
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
)
from rest_framework.response import Response

from api.filters import IngredientFilter, RecipeFilter
from api.pagination import RecipePagePagination
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (
    AvatarSerializer, CustomUserSerializer, IngredientSerializer,
    RecipeReadSerializer, RecipeWriteSerializer, ShortRecipeSerializer,
    SubscriptionSerializer, TagSerializer, UserListSerializer,
)
from recipes.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from users.models import Subscription

User = get_user_model()


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('name',)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = RecipePagePagination
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return (AllowAny(),)
        if self.action in ['update', 'partial_update', 'destroy']:
            return (IsAuthorOrReadOnly(),)
        if self.action == 'create':
            return (IsAuthenticated(),)
        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_authenticated:
            queryset = queryset.annotate(
                is_favorited=Exists(
                    Favorite.objects.filter(user=user, recipe=OuterRef('pk'))
                ),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(user=user, recipe=OuterRef('pk'))
                )
            )
        else:
            queryset = queryset.annotate(
                is_favorited=Value(False, output_field=BooleanField()),
                is_in_shopping_cart=Value(False, output_field=BooleanField())
            )
        return queryset

    def _save_and_respond(self, serializer, request, status_code):
        """Сохраняет рецепт и возвращает ответ RecipeReadSerializer."""
        recipe = serializer.save()
        annotated_recipe = self.get_queryset().get(pk=recipe.pk)
        response_serializer = RecipeReadSerializer(
            annotated_recipe, context={'request': request})
        return Response(response_serializer.data, status=status_code)

    def create(self, request, *args, **kwargs):
        """Создает новый рецепт."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data['author'] = request.user
        return self._save_and_respond(
            serializer, request, status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Обновляет существующий рецепт."""
        serializer = self.get_serializer(
            self.get_object(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return self._save_and_respond(serializer, request, status.HTTP_200_OK)

    def _handle_user_recipe_action(self, request, model, serializer_class,
                                   error_exists, error_not_exists):
        """Обрабатывает добавление/удаление рецепта в модели пользователя."""
        recipe = self.get_object()
        user = request.user

        if request.method == 'POST':
            if model.objects.filter(user=user, recipe=recipe).exists():
                return Response({'errors': error_exists},
                                status=status.HTTP_400_BAD_REQUEST)
            model.objects.create(user=user, recipe=recipe)
            serializer = serializer_class(
                recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        instance = model.objects.filter(user=user, recipe=recipe)
        if not instance.exists():
            return Response({'errors': error_not_exists},
                            status=status.HTTP_400_BAD_REQUEST)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        """Добавляет или удаляет рецепт из списка покупок пользователя."""
        return self._handle_user_recipe_action(
            request,
            ShoppingCart,
            ShortRecipeSerializer,
            'Рецепт уже в списке покупок',
            'Рецепт не в списке покупок'
        )

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        """Добавляет или удаляет рецепт из избранного пользователя."""
        return self._handle_user_recipe_action(
            request,
            Favorite,
            ShortRecipeSerializer,
            'Рецепт уже в избранном',
            'Рецепт не в избранном'
        )

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        recipes = Recipe.objects.filter(shopping_cart__user=user)
        ingredient_totals = {}
        for recipe in recipes:
            for ingredient in recipe.ingredient_relations.all():
                key = (ingredient.ingredient.name,
                       ingredient.ingredient.measurement_unit.name)
                if key in ingredient_totals:
                    ingredient_totals[key] += ingredient.amount
                else:
                    ingredient_totals[key] = ingredient.amount

        shopping_list = []
        for (name, unit), amount in ingredient_totals.items():
            shopping_list.append(f"{name} ({unit}) — {amount}")

        content = "\n".join(shopping_list)
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = ('attachment; '
                                           'filename="shopping_list.txt"')
        return response

    @action(detail=True, methods=['get'],
            permission_classes=[AllowAny], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = (f"{request.scheme}://{request.get_host()}"
                      f"/r/{recipe.short_code}")
        return Response({"short-link": short_link}, status=status.HTTP_200_OK)


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    pagination_class = RecipePagePagination

    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny(), ]
        return super().get_permissions()

    @action(detail=False, methods=['put'],
            permission_classes=[IsAuthenticated])
    def avatar(self, request):
        if 'avatar' not in request.data and 'avatar' not in request.FILES:
            return Response(
                {'avatar': 'Это поле обязательно.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        file = next(iter(request.FILES.values()), None)
        if file:
            data = {'avatar_input': file}
        else:
            if 'avatar' in request.data:
                file_data = request.data['avatar']
                if (isinstance(file_data, str)
                        and file_data.startswith('data:image')):
                    header, data = file_data.split(';base64,')
                    image_format = header.split('/')[-1]
                    if image_format not in ['png', 'jpeg', 'jpg']:
                        message = ('Неподдерживаемый формат. '
                                   'Используйте jpg или png')
                        return Response({'avatar': message},
                                        status=status.HTTP_400_BAD_REQUEST)
                    decoded_file = base64.b64decode(data)
                    filename = f'avatar_{request.user.id}.{image_format}'
                    file = ContentFile(decoded_file, name=filename)
                    data = {'avatar_input': file}

        serializer = AvatarSerializer(
            request.user, data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            avatar_url = (request.user.avatar.url
                          if request.user.avatar else None)
            return Response(
                {'avatar': avatar_url}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        """Удаляет аватар пользователя."""
        user = request.user
        if user.avatar:
            user.avatar.delete(save=True)
            user.avatar = None
            user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        user = request.user
        author = self.get_object()

        if user == author:
            return Response(
                {'errors': 'Нельзя подписаться на себя'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.method == 'POST':
            if Subscription.objects.filter(user=user, author=author).exists():
                return Response(
                    {'errors': 'Вы уже подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Subscription.objects.create(user=user, author=author)
            serializer = SubscriptionSerializer(
                author, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            subscription = Subscription.objects.filter(
                user=user, author=author)
            if not subscription.exists():
                return Response(
                    {'errors': 'Вы не подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(subscribers__user=user)
        page = self.paginate_queryset(queryset)
        serializer = SubscriptionSerializer(
            page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)
