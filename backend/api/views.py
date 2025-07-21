import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated

from api.serializers import (
    AvatarSerializer, CustomUserSerializer, IngredientSerializer,
    RecipeReadSerializer, RecipeWriteSerializer, TagSerializer)
from api.filters import IngredientFilter, RecipeFilter
from recipes.models import Tag, Recipe, Ingredient

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
    pagination_class = PageNumberPagination
    page_size = 6
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer

    @action(detail=False, methods=['put'], permission_classes=[IsAuthenticated])
    def avatar(self, request):
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
