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
import re


def build_transaction_admin_url(client_id, worksheet, classification_type, category):
    base = reverse("admin:profiles_transaction_changelist")
    params = f"?client__client_id={client_id}&worksheet={worksheet}&classification_type={classification_type}&category={category}"
    return base + params


def _sort_line_number(line):
    # Sorts line numbers like '16a', '16b', '10', '8', etc.
    m = re.match(r"(\d+)([a-zA-Z]*)", str(line))
    if m:
        num = int(m.group(1))
        suffix = m.group(2) or ""
        return (num, suffix)
    return (9999, str(line))


@staff_member_required
def irs_report(request):
    client_id = request.GET.get("client")
    form = ClientSelectForm(request.GET or None)
    categories = []
    total = 0
    selected_client = None
    business_categories = []
    worksheet_list = IRSWorksheet.objects.all()
    unmapped_business_cats = []
    if client_id:
        try:
            selected_client = BusinessProfile.objects.get(client_id=client_id)
        except BusinessProfile.DoesNotExist:
            selected_client = None
    if selected_client:
        worksheet = IRSWorksheet.objects.filter(name="6A").first()
        if worksheet:
            irs_categories = IRSExpenseCategory.objects.filter(worksheet=worksheet)
            # Map: IRS category name -> subtotal
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
            categories.sort(key=lambda c: _sort_line_number(c["line_number"]))
            # Fetch all business expense categories for this client and worksheet 6A
            business_cats = BusinessExpenseCategory.objects.filter(
                business=selected_client, worksheet=worksheet
            )
            irs_cat_names = set(cat.name for cat in irs_categories)
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
                entry = {
                    "name": bcat.category_name,
                    "subtotal": subtotal,
                    "tx_url": tx_url,
                    "mapped": bcat.category_name in irs_cat_names,
                }
                business_categories.append(entry)
                if not entry["mapped"]:
                    unmapped_business_cats.append(entry)
    context = {
        "client_id": client_id,
        "form": form,
        "categories": categories,
        "total": total,
        "selected_client": selected_client,
        "business_categories": business_categories,
        "worksheet_list": worksheet_list,
        "unmapped_business_cats": unmapped_business_cats,
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


@staff_member_required
def all_categories_report(request):
    client_id = request.GET.get("client")
    form = ClientSelectForm(request.GET or None)
    selected_client = None
    category_subtotals = {}
    total = 0
    category_links = {}
    if client_id:
        try:
            selected_client = BusinessProfile.objects.get(client_id=client_id)
        except BusinessProfile.DoesNotExist:
            selected_client = None
    if selected_client:
        txs = Transaction.objects.filter(client=selected_client)
        for tx in txs:
            key = (
                tx.worksheet or "(none)",
                tx.classification_type or "(none)",
                tx.category or "(none)",
            )
            if key not in category_subtotals:
                category_subtotals[key] = 0
            category_subtotals[key] += tx.amount or 0
            total += tx.amount or 0
            # Build admin URL for this category
            category_links[key] = build_transaction_admin_url(
                selected_client.client_id, key[0], key[1], key[2]
            )
    category_list = [
        {
            "worksheet": k[0],
            "classification_type": k[1],
            "category": k[2],
            "subtotal": v,
            "tx_url": category_links.get(k, ""),
        }
        for k, v in category_subtotals.items()
    ]
    category_list.sort(
        key=lambda x: (x["worksheet"], x["classification_type"], x["category"])
    )
    context = {
        "client_id": client_id,
        "form": form,
        "category_list": category_list,
        "total": total,
        "selected_client": selected_client,
    }
    return render(request, "reports/all_categories_report.html", context)


@staff_member_required
def irs_worksheet_report(request, worksheet_name):
    client_id = request.GET.get("client")
    form = ClientSelectForm(request.GET or None)
    categories = []
    total = 0
    selected_client = None
    business_categories = []
    unmapped_business_cats = []
    worksheet = IRSWorksheet.objects.filter(name=worksheet_name).first()
    if client_id:
        try:
            selected_client = BusinessProfile.objects.get(client_id=client_id)
        except BusinessProfile.DoesNotExist:
            selected_client = None
    if selected_client and worksheet:
        irs_categories = IRSExpenseCategory.objects.filter(worksheet=worksheet)
        for cat in irs_categories:
            subtotal = (
                Transaction.objects.filter(
                    client=selected_client,
                    worksheet=worksheet_name,
                    classification_type="business",
                    category=cat.name,
                ).aggregate(sum=Sum("amount"))["sum"]
                or 0
            )
            tx_url = build_transaction_admin_url(
                selected_client.client_id, worksheet_name, "business", cat.name
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
        categories.sort(key=lambda c: _sort_line_number(c["line_number"]))
        # Fetch all business expense categories for this client and worksheet
        business_cats = BusinessExpenseCategory.objects.filter(
            business=selected_client, worksheet=worksheet
        )
        irs_cat_names = set(cat.name for cat in irs_categories)
        for bcat in business_cats:
            subtotal = (
                Transaction.objects.filter(
                    client=selected_client,
                    worksheet=worksheet_name,
                    classification_type="business",
                    category=bcat.category_name,
                ).aggregate(sum=Sum("amount"))["sum"]
                or 0
            )
            tx_url = build_transaction_admin_url(
                selected_client.client_id,
                worksheet_name,
                "business",
                bcat.category_name,
            )
            entry = {
                "name": bcat.category_name,
                "subtotal": subtotal,
                "tx_url": tx_url,
                "mapped": bcat.category_name in irs_cat_names,
            }
            business_categories.append(entry)
            if not entry["mapped"]:
                unmapped_business_cats.append(entry)
    context = {
        "client_id": client_id,
        "form": form,
        "categories": categories,
        "total": total,
        "selected_client": selected_client,
        "business_categories": business_categories,
        "worksheet_name": worksheet_name,
        "worksheet": worksheet,
        "unmapped_business_cats": unmapped_business_cats,
    }
    return render(request, "reports/irs_worksheet_report.html", context)
