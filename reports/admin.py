from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.html import format_html
from django.db import models
from profiles.models import BusinessProfile
from .forms import ClientSelectForm
from .views import (
    irs_report,
    all_categories_report,
    interest_income_report,
    donations_report,
)


class ReportsProxy(models.Model):
    """Proxy model for Reports section in admin"""

    class Meta:
        verbose_name = "Report"
        verbose_name_plural = "Reports"
        app_label = "reports"
        managed = False


@admin.register(ReportsProxy)
class ReportsAdmin(admin.ModelAdmin):
    change_list_template = "admin/reports/reports_changelist.html"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def get_urls(self):
        urls = super().get_urls()
        info = self.model._meta.app_label, self.model._meta.model_name
        custom_urls = [
            path(
                "dashboard/",
                self.admin_site.admin_view(self.reports_dashboard),
                name=f"{info[0]}_{info[1]}_dashboard",
            ),
            path(
                "irs/",
                self.admin_site.admin_view(self.irs_report_view),
                name=f"{info[0]}_{info[1]}_irs",
            ),
            path(
                "irs/worksheet/<str:name>/",
                self.admin_site.admin_view(self.irs_worksheet_view),
                name=f"{info[0]}_{info[1]}_irs_worksheet",
            ),
            path(
                "categories/",
                self.admin_site.admin_view(self.categories_report_view),
                name=f"{info[0]}_{info[1]}_categories",
            ),
            path(
                "interest/",
                self.admin_site.admin_view(self.interest_income_report_view),
                name=f"{info[0]}_{info[1]}_interest",
            ),
            path(
                "donations/",
                self.admin_site.admin_view(self.donations_report_view),
                name=f"{info[0]}_{info[1]}_donations",
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        return self.reports_dashboard(request)

    def reports_dashboard(self, request):
        info = self.model._meta.app_label, self.model._meta.model_name
        context = {
            **self.admin_site.each_context(request),
            "title": "Reports Dashboard",
            "reports": [
                {
                    "title": "IRS 6A Report",
                    "url": f"{info[0]}_{info[1]}_irs",
                    "icon": "📊",
                    "description": "Generate IRS Schedule 6A reports for business expenses",
                },
                {
                    "title": "All Categories Report",
                    "url": f"{info[0]}_{info[1]}_categories",
                    "icon": "📋",
                    "description": "View transactions grouped by category",
                },
                {
                    "title": "Interest Income Report",
                    "url": f"{info[0]}_{info[1]}_interest",
                    "icon": "💰",
                    "description": "Track interest income and payments",
                },
                {
                    "title": "Donations Report",
                    "url": f"{info[0]}_{info[1]}_donations",
                    "icon": "🎁",
                    "description": "Track charitable donations and contributions",
                },
            ],
        }
        return render(request, "admin/reports/reports_dashboard.html", context)

    def irs_report_view(self, request):
        form = ClientSelectForm(request.GET or None)
        request.form = form
        return irs_report(request)

    def categories_report_view(self, request):
        form = ClientSelectForm(request.GET or None)
        request.form = form
        return all_categories_report(request)

    def interest_income_report_view(self, request):
        form = ClientSelectForm(request.GET or None)
        request.form = form
        request.title = "Interest Income Report"
        return interest_income_report(request)

    def donations_report_view(self, request):
        form = ClientSelectForm(request.GET or None)
        request.form = form
        request.title = "Charitable Donations Report"
        return donations_report(request)

    def irs_worksheet_view(self, request, name):
        form = ClientSelectForm(request.GET or None)
        request.form = form
        return irs_report(request, worksheet=name)
