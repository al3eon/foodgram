from django.conf import settings
from rest_framework.pagination import LimitOffsetPagination


class RecipeLimitOffsetPagination(LimitOffsetPagination):
    default_limit = settings.PAGINATION_DEFAULT_LIMIT
    max_limit = settings.PAGINATION_MAX_LIMIT
    page_size_query_param = 'limit'
    limit_query_param = 'limit'
    offset_query_param = 'offset'
