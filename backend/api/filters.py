from django.db.models import Q
from django_filters.rest_framework import FilterSet, CharFilter

from recipes.models import Ingredient, Recipe


class IngredientFilter(FilterSet):
    name = CharFilter(field_name='name', lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilter(FilterSet):
    tags = CharFilter(method='filter_tags')

    class Meta:
        model = Recipe
        fields = ('author', 'tags')

    def filter_tags(self, queryset, name, value):
        if value:
            tags = self.request.query_params.getlist('tags')
            if tags:
                q_objects = Q()
                for tag in tags:
                    q_objects |= Q(tags__slug=tag)
                queryset = queryset.filter(q_objects).distinct()
        return queryset