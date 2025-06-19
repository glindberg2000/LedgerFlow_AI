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
from django.db.models import Sum, Q
import re
from django.http import HttpResponse
from .pdf_utils import generate_interest_income_pdf, generate_donations_pdf


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


@staff_member_required
def interest_income_report(request):
    client_id = request.GET.get("client")
    form = (
        request.form
        if hasattr(request, "form")
        else ClientSelectForm(request.GET or None)
    )
    selected_client = None
    interest_transactions = []
    total = 0

    if client_id:
        try:
            selected_client = BusinessProfile.objects.get(client_id=client_id)
        except BusinessProfile.DoesNotExist:
            selected_client = None

    if selected_client:
        # Query for interest transactions using Q objects for OR condition
        interest_txs = (
            Transaction.objects.filter(client=selected_client)
            .filter(
                Q(description__icontains="INTEREST CREDIT")
                | Q(description__icontains="INTEREST PAYMENT")
            )
            .order_by("transaction_date")
            .select_related("statement_file")  # Add this to optimize queries
        )

        # Group transactions by source
        grouped_transactions = {}
        for tx in interest_txs:
            source = (
                "Interest Credit"
                if "CREDIT" in tx.description.upper()
                else "Interest Payment"
            )

            # Get statement file details if available
            statement_file = tx.statement_file
            account_info = {
                "account_number": tx.account_number
                or (statement_file.account_number if statement_file else None),
                "bank": statement_file.bank if statement_file else None,
                "statement_type": (
                    statement_file.statement_type if statement_file else None
                ),
                "file_name": (
                    statement_file.original_filename if statement_file else None
                ),
            }

            # Create a unique source key that includes the account info
            source_key = (
                f"{source}_{account_info['bank']}_{account_info['account_number']}"
            )

            if source_key not in grouped_transactions:
                grouped_transactions[source_key] = {
                    "source": source,
                    "transactions": [],
                    "subtotal": 0,
                    "account_info": account_info,
                }

            grouped_transactions[source_key]["transactions"].append(
                {
                    "transaction": tx,
                    "description": tx.description,
                    "source": tx.source,
                    "file_path": tx.file_path,
                    "transaction_date": tx.transaction_date,
                    "amount": tx.amount,
                    "account_number": tx.account_number,
                    "statement_file": account_info,
                }
            )
            grouped_transactions[source_key]["subtotal"] += tx.amount
            total += tx.amount

        interest_transactions = list(grouped_transactions.values())
        # Sort by bank name and account number
        interest_transactions.sort(
            key=lambda x: (
                x["account_info"]["bank"] or "",
                x["account_info"]["account_number"] or "",
                x["source"],
            )
        )

        # Check if PDF download was requested
        if request.GET.get("download") == "pdf":
            # Create the HttpResponse object with PDF headers
            response = HttpResponse(content_type="application/pdf")
            response["Content-Disposition"] = (
                f'attachment; filename="interest_income_report_{client_id}.pdf"'
            )

            # Generate the PDF
            generate_interest_income_pdf(
                response, selected_client, interest_transactions, total
            )
            return response

    context = {
        "title": getattr(request, "title", "Interest Income Report"),
        "client_id": client_id,
        "form": form,
        "selected_client": selected_client,
        "interest_transactions": interest_transactions,
        "total": total,
    }

    return render(request, "reports/interest_income_report.html", context)


@staff_member_required
def donations_report(request):
    client_id = request.GET.get("client")
    form = (
        request.form
        if hasattr(request, "form")
        else ClientSelectForm(request.GET or None)
    )
    selected_client = None
    donation_transactions = []
    total = 0

    if client_id:
        try:
            selected_client = BusinessProfile.objects.get(client_id=client_id)
        except BusinessProfile.DoesNotExist:
            selected_client = None

    if selected_client:
        # Query for donation transactions
        donation_txs = (
            Transaction.objects.filter(client=selected_client)
            .filter(
                Q(description__icontains="DONATION")
                | Q(description__icontains="CHARITABLE")
                | Q(category__icontains="DONATION")
                | Q(category__icontains="CHARITABLE")
            )
            .order_by("transaction_date")
        )

        # Group transactions by source/bank
        grouped_transactions = {}
        for tx in donation_txs:
            source = tx.source or "Unknown Source"
            bank = tx.statement_file.bank if tx.statement_file else "Unknown Bank"
            account = (
                tx.statement_file.account_number
                if tx.statement_file
                else "Unknown Account"
            )

            key = (source, bank, account)
            if key not in grouped_transactions:
                grouped_transactions[key] = {
                    "source": source,
                    "account_info": {
                        "bank": bank,
                        "account_number": account,
                        "statement_type": (
                            tx.statement_file.statement_type
                            if tx.statement_file
                            else None
                        ),
                    },
                    "transactions": [],
                    "subtotal": 0,
                }

            grouped_transactions[key]["transactions"].append(
                {
                    "transaction_date": tx.transaction_date,
                    "description": tx.description,
                    "amount": abs(tx.amount),  # Use absolute value for donations
                    "statement_file": {
                        "file_name": (
                            tx.statement_file.file_name if tx.statement_file else None
                        )
                    },
                    "source": source,
                }
            )
            grouped_transactions[key]["subtotal"] += abs(tx.amount)
            total += abs(tx.amount)

        # Convert to list and sort by bank name and source
        donation_transactions = sorted(
            grouped_transactions.values(),
            key=lambda x: (x["account_info"]["bank"], x["source"]),
        )

    context = {
        "form": form,
        "selected_client": selected_client,
        "donation_transactions": donation_transactions,
        "total": total,
    }

    # Handle PDF download
    if request.GET.get("download") == "pdf":
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="donations_report_{client_id}.pdf"'
        )
        generate_donations_pdf(response, selected_client, donation_transactions, total)
        return response

    return render(request, "reports/donations_report.html", context)
