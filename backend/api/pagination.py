from django.conf import settings
from rest_framework.pagination import PageNumberPagination


class RecipePagePagination(PageNumberPagination):
    page_size = settings.PAGINATION_PAGE_SIZE
    max_page_size = settings.PAGINATION_MAX_PAGE_SIZE
    page_size_query_param = 'limit'
    page_query_param = 'page'
