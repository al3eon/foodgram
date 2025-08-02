from django.http import HttpResponse,HttpResponseRedirect
from django.views import View

from .models import Recipe

class ShortLinkRedirectView(View):
    def get(self, request, short_code):
        try:
            recipe = Recipe.objects.get(short_code=short_code)
            return HttpResponseRedirect(f"/recipes/{recipe.id}/")
        except Recipe.DoesNotExist:
            return HttpResponse(status=404)