from django.urls import path
from . import views

urlpatterns = [
    path("upload/", views.upload_workbook, name="organizer_workbook_upload"),
    path("<int:pk>/", views.workbook_detail, name="organizer_workbook_detail"),
]
