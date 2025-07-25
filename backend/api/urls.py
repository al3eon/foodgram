from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (CustomUserViewSet, IngredientViewSet, RecipeViewSet,
                    ShortLinkRedirectView, TagViewSet)

router = DefaultRouter()
router.register('tags', TagViewSet, basename='tags')
router.register('recipes', RecipeViewSet, basename='recipes')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('users', CustomUserViewSet, basename='users')

urlpatterns = [
    path('r/<str:short_code>/', ShortLinkRedirectView.as_view(),
         name='short-link-redirect'),
    path('users/me/avatar/', CustomUserViewSet.as_view(
        {'put': 'avatar', 'delete': 'delete_avatar'}
    ), name='user-avatar'),
    path('', include(router.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
