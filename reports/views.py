from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
from profiles.models import (
    BusinessProfile,
    Transaction,
    IRSWorksheet,
    IRSExpenseCategory,
    BusinessExpenseCategory,
    StatementFile,
)
from .forms import ClientSelectForm
from django.db.models import Sum, Q
import re
from django.http import HttpResponse, Http404
from .pdf_utils import (
    generate_interest_income_pdf,
    generate_donations_pdf,
    generate_categories_pdf,
    generate_irs_pdf,
)
from datetime import datetime
from django.contrib.auth.decorators import login_required
import os
from decimal import Decimal


@login_required
def download_statement_file(request, file_id):
    statement_file = get_object_or_404(StatementFile, pk=file_id)
    if not statement_file.file:
        raise Http404("File not found")

    file_path = statement_file.file.path
    if os.path.exists(file_path):
        with open(file_path, "rb") as fh:
            response = HttpResponse(fh.read(), content_type="application/octet-stream")
            response["Content-Disposition"] = (
                f'inline; filename="{statement_file.original_filename}"'
            )
            return response
    raise Http404


@staff_member_required
def index(request):
    """Landing page for reports showing all available report types."""
    client_id = request.GET.get("client")
    form = ClientSelectForm(request.GET or None)
    selected_client = None
    if client_id:
        try:
            selected_client = BusinessProfile.objects.get(client_id=client_id)
        except BusinessProfile.DoesNotExist:
            selected_client = None

    # Define available reports
    reports = [
        {
            "name": "IRS Form 6A",
            "description": "Generate IRS Form 6A report with expense categorization.",
            "url": reverse("irs_report"),
            "icon": "📋",
        },
        {
            "name": "All Categories",
            "description": "View transactions grouped by all expense categories.",
            "url": reverse("all_categories_report"),
            "icon": "📊",
        },
        {
            "name": "Interest Income",
            "description": "Track all interest income from various sources.",
            "url": reverse("interest_income_report"),
            "icon": "💰",
        },
        {
            "name": "Business Report",
            "description": "Business-specific transaction analysis.",
            "url": reverse("business_report"),
            "icon": "🏢",
        },
        {
            "name": "Personal Report",
            "description": "Personal transaction analysis.",
            "url": reverse("personal_report"),
            "icon": "👤",
        },
        {
            "name": "Combined Report",
            "description": "Combined view of business and personal transactions.",
            "url": reverse("combined_report"),
            "icon": "🔄",
        },
    ]

    # Add client_id to URLs if a client is selected
    if selected_client:
        for report in reports:
            if "?" in report["url"]:
                report["url"] += f"&client={client_id}"
            else:
                report["url"] += f"?client={client_id}"

    return render(
        request,
        "reports/index.html",
        {
            "form": form,
            "selected_client": selected_client,
            "reports": reports,
            "title": "Reports Dashboard",
        },
    )


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


def _get_base_context(request):
    """Gets the base context for a report view, including admin context if available."""
    context = {
        "title": getattr(request, "title", "Report"),
    }
    if hasattr(request, "admin_site_context"):
        context.update(request.admin_site_context)
    return context


@staff_member_required
@login_required
def irs_report(request, worksheet=None):
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
    context = _get_base_context(request)
    context.update(
        {
            "client_id": client_id,
            "form": form,
            "categories": categories,
            "total": total,
            "selected_client": selected_client,
            "business_categories": business_categories,
            "worksheet_list": worksheet_list,
            "unmapped_business_cats": unmapped_business_cats,
        }
    )
    if hasattr(request, "admin_site_context"):
        context.update(request.admin_site_context)

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
@login_required
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
    context = _get_base_context(request)
    context.update(
        {
            "client_id": client_id,
            "form": form,
            "category_list": category_list,
            "total": total,
            "selected_client": selected_client,
        }
    )
    if hasattr(request, "admin_site_context"):
        context.update(request.admin_site_context)
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


@staff_member_required
@login_required
def interest_income_report(request):
    client_id = request.GET.get("client")
    time_frame = "All Time"
    interest_transactions_grouped = []
    total = 0
    client = None

    if client_id:
        try:
            client = BusinessProfile.objects.get(client_id=client_id)
            interest_txs_query = (
                Transaction.objects.filter(
                    Q(statement_file__client__client_id=client_id)
                    & (
                        Q(description__icontains="INTEREST CREDIT")
                        | Q(description__icontains="INTEREST PAYMENT")
                    )
                )
                .order_by("statement_file__bank", "transaction_date")
                .select_related("statement_file")
            )

            total = interest_txs_query.aggregate(Sum("amount"))["amount__sum"] or 0

            # Group transactions by statement bank
            grouped = {}
            for tx in interest_txs_query:
                source = tx.statement_file.bank
                if source not in grouped:
                    grouped[source] = {
                        "transactions": [],
                        "subtotal": 0,
                        "account_info": {
                            "bank": tx.statement_file.bank,
                            "account_number": tx.statement_file.account_number,
                            "statement_type": tx.statement_file.statement_type,
                        },
                    }
                grouped[source]["transactions"].append(tx)
                grouped[source]["subtotal"] += tx.amount

            interest_transactions_grouped = [
                {"source": key, **value} for key, value in grouped.items()
            ]

            if "download" in request.GET and request.GET["download"] == "pdf":
                response = HttpResponse(content_type="application/pdf")
                response["Content-Disposition"] = (
                    f'attachment; filename="interest_income_report_{client.client_id}.pdf"'
                )
                generate_interest_income_pdf(
                    response, client, interest_transactions_grouped, total
                )
                return response

        except BusinessProfile.DoesNotExist:
            pass  # client not found

    context = _get_base_context(request)
    context.update(
        {
            "interest_transactions": interest_transactions_grouped,
            "total": total,
            "time_frame": time_frame,
            "selected_client": client,
        }
    )
    return render(request, "reports/interest_income_report.html", context)


@staff_member_required
@login_required
def donations_report(request):
    client_id = request.GET.get("client")
    form = ClientSelectForm(request.GET or None)
    selected_client = None
    donation_transactions = []
    total_donations = Decimal("0.00")

    if client_id:
        selected_client = get_object_or_404(BusinessProfile, client_id=client_id)

        # Correctly filter for transactions that are donations.
        # This includes looking at payee names and specific categories.
        donation_payees_qs = Q()
        donation_keywords = [
            "GOODWILL",
            "SALVATION ARMY",
            "DONATION",
            "CHARITY",
            "RESCUE",
            "SOUTHWEST ANIMAL",
        ]
        for keyword in donation_keywords:
            donation_payees_qs |= Q(payee__icontains=keyword)

        transactions = (
            Transaction.objects.filter(
                Q(client=selected_client),
                (
                    Q(category__icontains="Donation")
                    | Q(category__icontains="Charity")
                    | donation_payees_qs
                ),
            )
            .exclude(
                Q(description__icontains="Card Purchase")
                | Q(description__icontains="POS Purchase")
            )
            .order_by("transaction_date")
        )

        # Group transactions by source (e.g., bank account)
        grouped_transactions = {}
        for tx in transactions:
            source_key = (
                tx.statement_file.get_source_display()
                if tx.statement_file
                else "Unknown Source"
            )
            if source_key not in grouped_transactions:
                bank = tx.statement_file.bank if tx.statement_file else "N/A"
                account_number = (
                    tx.statement_file.account_number if tx.statement_file else "N/A"
                )
                statement_type = (
                    tx.statement_file.statement_type if tx.statement_file else "N/A"
                )

                grouped_transactions[source_key] = {
                    "source": source_key,
                    "account_info": {
                        "bank": bank,
                        "account_number": account_number,
                        "statement_type": statement_type,
                    },
                    "transactions": [],
                    "subtotal": Decimal("0.00"),
                }

            # Ensure amount is negative for expenses
            amount = -abs(tx.amount)
            grouped_transactions[source_key]["transactions"].append(tx)
            grouped_transactions[source_key]["subtotal"] += amount

        donation_transactions = list(grouped_transactions.values())
        total_donations = sum(g["subtotal"] for g in donation_transactions)

    # Handle PDF download
    if "download" in request.GET and selected_client:
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="donations_report_{selected_client.client_id}.pdf"'
        )
        generate_donations_pdf(
            response, selected_client, donation_transactions, total_donations
        )
        return response

    context = {
        "form": form,
        "selected_client": selected_client,
        "donation_transactions": donation_transactions,
        "total_donations": total_donations,
        "title": "Charitable Donations Report",
    }
    if hasattr(request, "admin_site_context"):
        context.update(request.admin_site_context)
    return render(request, "reports/donations_report.html", context)
