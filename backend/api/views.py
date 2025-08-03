from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef, Sum, Value
from django.db.models.fields import BooleanField
from django.http import HttpResponse
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
from api.serializers import (
    AvatarSerializer, IngredientSerializer, ProfileSerializer,
    RecipeReadSerializer, RecipeWriteSerializer, ShortRecipeSerializer,
    SubscriptionSerializer, TagSerializer
)
from recipes.models import (
    Favorite, Ingredient, Recipe,
    RecipeIngredient, ShoppingCart, Tag
)
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

    def get_queryset(self):
        user = self.request.user
        return Recipe.objects.with_user_annotations(user)

    def partial_update(self, request, *args, **kwargs):
        if not self.get_object().author == request.user:
            return Response(
                {'detail': 'У вас нет прав на редактирование этого рецепта.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Удаляет рецепт."""
        if not self.get_object().author == request.user:
            return Response(
                {'detail': 'У вас нет прав на удаление этого рецепта.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    def _handle_user_recipe_action(self, request, model, serializer_class,
                                   error_exists, error_not_exists):
        """Обрабатывает добавление/удаление рецепта в модели пользователя."""
        recipe = self.get_object()
        user = request.user

        if request.method == 'POST':
            instance, created = model.objects.get_or_create(
                user=user, recipe=recipe)
            if not created:
                return Response(
                    {'errors': error_exists},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = serializer_class(recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        deleted, _ = model.objects.filter(user=user, recipe=recipe).delete()
        if not deleted:
            return Response(
                {'errors': error_not_exists},
                status=status.HTTP_400_BAD_REQUEST
            )
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
        ingredient_totals = (
            RecipeIngredient.objects
            .filter(recipe__shoppingcart__user=user)
            .values('ingredient__name', 'ingredient__measurement_unit__name')
            .annotate(total_amount=Sum('amount'))
            .order_by('ingredient__name')
        )

        shopping_list = [
            (f"{item['ingredient__name']} ("
             f"{item['ingredient__measurement_unit__name']}) — "
             f"{item['total_amount']}")
            for item in ingredient_totals
        ]

        content = '\n'.join(shopping_list)
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = ('attachment; '
                                           'filename="shopping_list.txt"')
        return response

    @action(detail=True, methods=['get'],
            permission_classes=[AllowAny], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = request.build_absolute_uri(f'/r/{recipe.short_code}')
        return Response({'short-link': short_link}, status=status.HTTP_200_OK)


class ProfileViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = ProfileSerializer
    pagination_class = RecipePagePagination

    def get_serializer_class(self):
        if self.action == 'avatar':
            return AvatarSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny(), ]
        return super().get_permissions()

    @action(detail=False, methods=['put'],
            permission_classes=[IsAuthenticated])
    def avatar(self, request):
        """Обновляет аватар пользователя"""
        serializer = self.get_serializer(
            request.user, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        avatar_url = request.user.avatar.url if request.user.avatar else None
        return Response({'avatar': avatar_url}, status=status.HTTP_200_OK)

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

        if request.method == 'POST':
            if user == author:
                return Response(
                    {'errors': 'Нельзя подписаться на себя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            instance, created = Subscription.objects.get_or_create(
                user=user, author=author)
            if not created:
                return Response(
                    {'errors': 'Вы уже подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = SubscriptionSerializer(
                author, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        deleted, _ = Subscription.objects.filter(
            user=user, author=author).delete()
        if not deleted:
            return Response(
                {'errors': 'Вы не подписаны на этого пользователя'},
                status=status.HTTP_400_BAD_REQUEST
            )
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
