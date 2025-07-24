from django.db.models import Q
from django_filters.rest_framework import CharFilter, filters, FilterSet

from recipes.models import Ingredient, Recipe


class IngredientFilter(FilterSet):
    name = CharFilter(field_name='name', lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilter(FilterSet):
    tags = CharFilter(method='filter_tags')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart')
    is_favorited = filters.BooleanFilter(method='filter_is_favorited')

    class Meta:
        model = Recipe
        fields = ('author', 'tags', 'is_in_shopping_cart', 'is_favorited')

    def filter_tags(self, queryset, name, value):
        tags = self.request.query_params.getlist('tags')
        if tags:
            q_objects = Q()
            for tag in tags:
                q_objects |= Q(tags__slug=tag)
            queryset = queryset.filter(q_objects).distinct()
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        if value and self.request.user.is_authenticated:
            return queryset.filter(shopping_cart__user=self.request.user)
        return queryset

    def filter_is_favorited(self, queryset, name, value):
        if value and self.request.user.is_authenticated:
            return queryset.filter(favorites__user=self.request.user)
        return queryset
