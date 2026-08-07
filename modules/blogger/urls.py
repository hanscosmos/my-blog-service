from django.urls import path
from .views import *

urlpatterns = [
    path('profile/get', get_blogger_profile, name='get_blogger_profile'),
    path('profile/update', update_blogger_profile, name='update_blogger_profile'),
]
