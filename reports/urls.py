from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    # Make index the default landing page
    path("", views.index, name="reports_index"),
    path("irs/", views.irs_report, name="irs_report"),
    path(
        "irs/worksheet/<str:worksheet_name>/",
        views.irs_worksheet_report,
        name="irs_worksheet_report",
    ),
    path("business/", views.business_report, name="business_report"),
    path("combined/", views.combined_report, name="combined_report"),
    path("personal/", views.personal_report, name="personal_report"),
    path("all_categories/", views.all_categories_report, name="all_categories_report"),
    path(
        "interest_income/", views.interest_income_report, name="interest_income_report"
    ),
    path("donations/", views.donations_report, name="donations_report"),
    path(
        "download/<int:file_id>/",
        views.download_statement_file,
        name="download_statement_file",
    ),
]
