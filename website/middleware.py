from .models import UserActivity
from django.utils import timezone

class UserActivityMiddleware:

    def __init__(self,get_response):
        self.get_response = get_response

    def __call__(self,request):
        response = self.get_response(request)
        if request.user.is_authenticated:
            UserActivity.objects.create(
                user=request.user,
                path=request.path,
                action="Page Visited",
                timestamp=timezone.now()

        )
       
        return response