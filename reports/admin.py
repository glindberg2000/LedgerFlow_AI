from django.contrib import admin
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.db import models
from profiles.models import BusinessProfile


class ReportsProxy(BusinessProfile):
    class Meta:
        proxy = True
        verbose_name = "Reports"
        verbose_name_plural = "Reports"


class ReportsAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        return HttpResponseRedirect("/reports/irs/")


admin.site.register(ReportsProxy, ReportsAdmin)

# This is a placeholder; actual report views will be custom admin views.
