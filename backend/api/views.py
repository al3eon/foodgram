import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse, HttpResponseRedirect
from django.views import View
from djoser.views import UserViewSet
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from rest_framework.permissions import AllowAny, IsAuthenticated

from api.serializers import (
    AvatarSerializer, CustomUserSerializer, IngredientSerializer,
    RecipeReadSerializer, RecipeWriteSerializer, TagSerializer, ShoppingCartSerializer, FavoriteSerializer,
    SubscriptionSerializer, UserListSerializer)
from api.filters import IngredientFilter, RecipeFilter
from recipes.models import Tag, Recipe, Ingredient, ShoppingCart, Favorite
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
    filterset_fields = ('name',)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = LimitOffsetPagination
    page_size = 6
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipe = serializer.save(author=self.request.user)
        response_serializer = RecipeReadSerializer(recipe, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        recipe = serializer.save()
        response_serializer = RecipeReadSerializer(recipe, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        user = request.user

        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'errors': 'Рецепт уже в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            shopping_cart = ShoppingCart.objects.create(user=user, recipe=recipe)
            serializer = ShoppingCartSerializer(shopping_cart, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            shopping_cart = ShoppingCart.objects.filter(user=user, recipe=recipe)
            if not shopping_cart.exists():
                return Response(
                    {'errors': 'Рецепт не в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            shopping_cart.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        recipes = Recipe.objects.filter(shopping_cart__user=user)
        ingredient_totals = {}
        for recipe in recipes:
            for ingredient in recipe.ingredients.all():
                key = (ingredient.ingredient.name, ingredient.ingredient.measurement_unit.name)
                if key in ingredient_totals:
                    ingredient_totals[key] += ingredient.amount
                else:
                    ingredient_totals[key] = ingredient.amount

        shopping_list = []
        for (name, unit), amount in ingredient_totals.items():
            shopping_list.append(f"{name} ({unit}) — {amount}")

        content = "\n".join(shopping_list)
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return response

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user

        if request.method == 'POST':
            if Favorite.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'errors': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            favorite = Favorite.objects.create(user=user, recipe=recipe)
            serializer = FavoriteSerializer(favorite, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            favorite = Favorite.objects.filter(user=user, recipe=recipe)
            if not favorite.exists():
                return Response(
                    {'errors': 'Рецепт не в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], permission_classes=[AllowAny], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = f"{request.scheme}://{request.get_host()}/api/r/{recipe.short_code}"
        return Response({"short-link": short_link}, status=status.HTTP_200_OK)


class ShortLinkRedirectView(View):
    def get(self, request, short_code):
        try:
            recipe = Recipe.objects.get(short_code=short_code)
            return HttpResponseRedirect(f"/recipes/{recipe.id}/")
        except Recipe.DoesNotExist:
            return HttpResponse(status=404)


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny(),]
        return super().get_permissions()

    @action(detail=False, methods=['put'], permission_classes=[IsAuthenticated])
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
                if isinstance(file_data, str) and file_data.startswith('data:image'):
                    header, data = file_data.split(';base64,')
                    image_format = header.split('/')[-1]
                    if image_format not in ['png', 'jpeg', 'jpg']:
                        return Response({'avatar': 'Неподдерживаемый формат. Используйте jpg или png'},
                                        status=status.HTTP_400_BAD_REQUEST)
                    decoded_file = base64.b64decode(data)
                    filename = f'avatar_{request.user.id}.{image_format}'
                    file = ContentFile(decoded_file, name=filename)
                    data = {'avatar_input': file}

        serializer = AvatarSerializer(request.user, data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'avatar': request.user.avatar.url if request.user.avatar else None},
                            status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        user = request.user
        if user.avatar:
            user.avatar.delete(save=True)
            user.avatar = None
            user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
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
            serializer = SubscriptionSerializer(author, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            subscription = Subscription.objects.filter(user=user, author=author)
            if not subscription.exists():
                return Response(
                    {'errors': 'Вы не подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(subscribers__user=user)
        page = self.paginate_queryset(queryset)
        serializer = SubscriptionSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)
