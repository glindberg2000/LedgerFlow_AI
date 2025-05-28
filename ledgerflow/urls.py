from django.contrib import admin
from django.urls import path, include
from django.contrib.admin.views.decorators import staff_member_required
from profiles.parsers_utilities.admin import test_parser_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("profiles/", include("profiles.urls")),
    path("reports/", include("reports.urls")),
    path(
        "utilities/test_parser/",
        staff_member_required(test_parser_view),
        name="parsers_utilities_test_parser",
    ),
]
