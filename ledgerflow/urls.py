from django.contrib import admin
from django.urls import path, include
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("profiles/", include("profiles.urls")),
    path("reports/", include("reports.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
