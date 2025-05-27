from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
from profiles.models import (
    BusinessProfile,
    Transaction,
    IRSWorksheet,
    IRSExpenseCategory,
    BusinessExpenseCategory,
)
from .forms import ClientSelectForm
from django.db.models import Sum


def build_transaction_admin_url(client_id, worksheet, classification_type, category):
    base = reverse("admin:profiles_transaction_changelist")
    params = f"?client__client_id={client_id}&worksheet={worksheet}&classification_type={classification_type}&category={category}"
    return base + params


@staff_member_required
def irs_report(request):
    client_id = request.GET.get("client")
    form = ClientSelectForm(request.GET or None)
    categories = []
    total = 0
    selected_client = None
    business_categories = []
    if client_id:
        try:
            selected_client = BusinessProfile.objects.get(client_id=client_id)
        except BusinessProfile.DoesNotExist:
            selected_client = None
    if selected_client:
        worksheet = IRSWorksheet.objects.filter(name="6A").first()
        if worksheet:
            irs_categories = IRSExpenseCategory.objects.filter(worksheet=worksheet)
            for cat in irs_categories:
                subtotal = (
                    Transaction.objects.filter(
                        client=selected_client,
                        worksheet="6A",
                        classification_type="business",
                        category=cat.name,
                    ).aggregate(sum=Sum("amount"))["sum"]
                    or 0
                )
                tx_url = build_transaction_admin_url(
                    selected_client.client_id, "6A", "business", cat.name
                )
                categories.append(
                    {
                        "name": cat.name,
                        "line_number": cat.line_number,
                        "subtotal": subtotal,
                        "tx_url": tx_url,
                    }
                )
                total += subtotal
            # Fetch business expense categories for this client and worksheet 6A
            business_cats = BusinessExpenseCategory.objects.filter(
                business=selected_client, worksheet=worksheet
            )
            for bcat in business_cats:
                subtotal = (
                    Transaction.objects.filter(
                        client=selected_client,
                        worksheet="6A",
                        classification_type="business",
                        category=bcat.category_name,
                    ).aggregate(sum=Sum("amount"))["sum"]
                    or 0
                )
                tx_url = build_transaction_admin_url(
                    selected_client.client_id, "6A", "business", bcat.category_name
                )
                business_categories.append(
                    {
                        "name": bcat.category_name,
                        "subtotal": subtotal,
                        "tx_url": tx_url,
                    }
                )
    context = {
        "client_id": client_id,
        "form": form,
        "categories": categories,
        "total": total,
        "selected_client": selected_client,
        "business_categories": business_categories,
    }
    return render(request, "reports/irs_report.html", context)


@staff_member_required
def business_report(request):
    client_id = request.GET.get("client")
    context = {"client_id": client_id}
    return render(request, "reports/business_report.html", context)


@staff_member_required
def combined_report(request):
    client_id = request.GET.get("client")
    context = {"client_id": client_id}
    return render(request, "reports/combined_report.html", context)


@staff_member_required
def personal_report(request):
    client_id = request.GET.get("client")
    context = {"client_id": client_id}
    return render(request, "reports/personal_report.html", context)
