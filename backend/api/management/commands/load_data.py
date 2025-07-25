import json
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from recipes.models import Ingredient, Unit, Tag, Recipe, RecipeIngredient

User = get_user_model()


class Command(BaseCommand):
    help = 'Загружает данные из JSON'

    def handle(self, *args, **kwargs):
        with open(os.path.join(settings.BASE_DIR, 'data', 'initial_data.json'),
                  encoding='utf-8') as f:
            data = json.load(f)
            self.load_users(data['users'])
            self.load_units(data['units'])
            self.load_ingredients(data['ingredients'])
            self.load_tags(data['tags'])
            self.load_recipes(data['recipes'])

    def load_users(self, users):
        for user in users:
            u, _ = User.objects.get_or_create(
                username=user['username'],
                email=user['email'],
                defaults={
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'is_staff': user.get('is_staff', False)
                }
            )
            u.set_password(user['password'])
            u.save()

    def load_units(self, units):
        for unit in units:
            Unit.objects.get_or_create(name=unit['name'])

    def load_ingredients(self, ingredients):
        for ingredient in ingredients:
            unit, _ = Unit.objects.get_or_create(
                name=ingredient['measurement_unit'])
            Ingredient.objects.get_or_create(
                name=ingredient['name'], measurement_unit=unit)

    def load_tags(self, tags):
        for tag in tags:
            Tag.objects.get_or_create(name=tag['name'], slug=tag['slug'])

    def load_recipes(self, recipes):
        for recipe in recipes:
            r, _ = Recipe.objects.get_or_create(
                name=recipe['name'],
                author=User.objects.get(username=recipe['author']),
                text=recipe['text'],
                cooking_time=recipe['cooking_time']
            )
            for tag_slug in recipe['tags']:
                r.tags.add(Tag.objects.get(slug=tag_slug))
            for ingredient_data in recipe['ingredients']:
                ingredient = Ingredient.objects.get(
                    name=ingredient_data['name'])
                RecipeIngredient.objects.get_or_create(
                    recipe=r,
                    ingredient=ingredient,
                    amount=ingredient_data['amount']
                )
