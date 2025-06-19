from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from decimal import Decimal
from django.utils import timezone


def generate_interest_income_pdf(response, client, interest_transactions, total):
    """Generate a PDF report for interest income transactions."""

    # Create the PDF document
    doc = SimpleDocTemplate(
        response,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )

    # Container for the 'Flowable' objects
    elements = []

    # Get styles
    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    subtitle_style = styles["Heading2"]
    normal_style = styles["Normal"]

    # Add custom header style
    header_style = ParagraphStyle(
        "CustomHeader", parent=styles["Heading2"], fontSize=10, spaceAfter=20
    )

    # Add title
    elements.append(Paragraph("Interest Income Report", title_style))
    elements.append(Spacer(1, 12))

    # Add business information
    elements.append(Paragraph(f"Client ID: {client.client_id}", header_style))
    if client.business_type:
        elements.append(
            Paragraph(f"Business Type: {client.business_type}", header_style)
        )
    if client.business_description:
        elements.append(
            Paragraph(
                f"Business Description: {client.business_description}", header_style
            )
        )
    if client.contact_info:
        elements.append(
            Paragraph(f"Contact Information: {client.contact_info}", header_style)
        )
    if client.location:
        elements.append(Paragraph(f"Location: {client.location}", header_style))

    elements.append(Spacer(1, 20))

    # Add report generation timestamp
    elements.append(
        Paragraph(
            f"Report Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}",
            normal_style,
        )
    )
    elements.append(Spacer(1, 20))

    # Process each group of transactions
    for group in interest_transactions:
        # Add group header
        elements.append(Paragraph(f"{group['source']}", subtitle_style))

        # Add account information
        if group["account_info"].get("bank"):
            elements.append(
                Paragraph(f"Bank: {group['account_info']['bank']}", normal_style)
            )
        if group["account_info"].get("account_number"):
            elements.append(
                Paragraph(
                    f"Account: {group['account_info']['account_number']}", normal_style
                )
            )
        if group["account_info"].get("statement_type"):
            elements.append(
                Paragraph(
                    f"Account Type: {group['account_info']['statement_type']}",
                    normal_style,
                )
            )

        elements.append(Spacer(1, 12))

        # Create transaction table
        table_data = [["Date", "Description", "Source", "Amount", "Source File"]]

        # Add transactions to table
        for tx in group["transactions"]:
            table_data.append(
                [
                    tx["transaction_date"].strftime("%Y-%m-%d"),
                    tx["description"],
                    tx["source"] or "N/A",
                    f"${tx['amount']:.2f}",
                    tx["statement_file"]["file_name"] or "N/A",
                ]
            )

        # Add subtotal row
        table_data.append(["Subtotal", "", "", f"${group['subtotal']:.2f}", ""])

        # Create the table
        table = Table(table_data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("ALIGN", (3, 1), (3, -1), "RIGHT"),  # Right-align amounts
                ]
            )
        )

        elements.append(table)
        elements.append(Spacer(1, 20))

    # Add total
    elements.append(Paragraph(f"Total Interest Income: ${total:.2f}", subtitle_style))

    # Build the PDF
    doc.build(elements)


def format_currency(amount):
    """Helper function to format currency values."""
    if isinstance(amount, (int, float, Decimal)):
        return f"${amount:,.2f}"
    return "N/A"
