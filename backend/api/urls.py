from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (IngredientViewSet, RecipeViewSet,
                    ProfileViewSet, TagViewSet)

router = DefaultRouter()
router.register('tags', TagViewSet, basename='tags')
router.register('recipes', RecipeViewSet, basename='recipes')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('users', ProfileViewSet, basename='users')

urlpatterns = [
    path('users/me/avatar/', ProfileViewSet.as_view(
        {'put': 'avatar', 'delete': 'delete_avatar'}
    ), name='user-avatar'),
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
