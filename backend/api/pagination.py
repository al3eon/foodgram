from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class CustomLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 6
    max_limit = 100
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    page_query_param = 'page'

    def get_offset(self, request):
        page = int(request.query_params.get(self.page_query_param, 1))
        limit = int(request.query_params.get(
            self.limit_query_param, self.default_limit))
        return (page - 1) * limit

    def get_paginated_response(self, data):
        page = int(self.request.query_params.get(self.page_query_param, 1))
        limit = int(self.request.query_params.get(
            self.limit_query_param, self.default_limit))
        offset = (page - 1) * limit
        next_page = None
        if self.count > offset + limit:
            next_page = (
                f"{self.request.build_absolute_uri(self.request.path)}"
                f"?limit={limit}&offset={offset + limit}")
        previous_page = None
        if offset > 0:
            previous_page = (
                f"{self.request.build_absolute_uri(self.request.path)}"
                f"?limit={limit}&offset={max(offset - limit, 0)}")
        return Response({
            'count': self.count,
            'next': next_page,
            'previous': previous_page,
            'results': data
        })
