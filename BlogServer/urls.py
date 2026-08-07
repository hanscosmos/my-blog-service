from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('user/', include('modules.user.urls')),
    path('authority/', include('modules.authority.urls')),
    path('resource/', include('modules.resource.urls')),
    path('article/', include('modules.article.urls')),
    path('sys/', include('modules.system.urls')),
    path('client/', include('modules.client.urls')),
    path('blogger/', include('modules.blogger.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
