from django.conf import settings
from rest_framework.pagination import PageNumberPagination


class RecipePagePagination(PageNumberPagination):
    default_limit = settings.PAGINATION_DEFAULT_LIMIT
    max_limit = settings.PAGINATION_MAX_LIMIT
    page_size_query_param = 'limit'
    page_query_param = 'page'
