from django.urls import path

from .views import ShortLinkRedirectView

urlpatterns = [
    path('r/<str:short_code>/', ShortLinkRedirectView.as_view(),
         name='short-link-redirect'),
]