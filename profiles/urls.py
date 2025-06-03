from django.urls import path
from . import views

urlpatterns = [
    path("upload-transactions/", views.upload_transactions, name="upload-transactions"),
    path(
        "upload-statement-files/",
        views.upload_statement_files,
        name="upload-statement-files",
    ),
    path("", views.BusinessProfileListView.as_view(), name="profile-list"),
]
