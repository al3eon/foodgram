from django.contrib import admin
from .models import (
    Recipe, Ingredient, Tag, RecipeIngredient,
    Favorite, ShoppingCart, Unit)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    raw_id_fields = ('ingredient',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'favorite_count')
    search_fields = ('name', 'author__username', 'author__email')
    list_filter = ('tags', 'author')
    list_per_page = 20
    raw_id_fields = ('author',)
    filter_horizontal = ('tags',)  # Убрали 'ingredients'
    inlines = [RecipeIngredientInline]

    def favorite_count(self, obj):
        return obj.favorites.count()
    favorite_count.short_description = 'Добавлено в избранное'


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('measurement_unit',)
    list_per_page = 20


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')
    list_per_page = 20


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')
    search_fields = ('recipe__name', 'ingredient__name')
    list_per_page = 20
    raw_id_fields = ('recipe', 'ingredient')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')
    list_filter = ('user',)
    list_per_page = 20
    raw_id_fields = ('user', 'recipe')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')
    list_filter = ('user',)
    list_per_page = 20
    raw_id_fields = ('user', 'recipe')


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_per_page = 20
