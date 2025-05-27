from django.urls import path
from . import views

urlpatterns = [
    path("irs/", views.irs_report, name="irs_report"),
    path("business/", views.business_report, name="business_report"),
    path("combined/", views.combined_report, name="combined_report"),
    path("personal/", views.personal_report, name="personal_report"),
]
