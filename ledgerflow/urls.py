from django.contrib import admin
from django.urls import path, include

# from django.urls import include
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("reports/", include(("reports.urls", "reports"), namespace="reports")),
    # path('profiles/', include('profiles.urls')),
    # ... (comment out any other custom app URLs) ...
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
