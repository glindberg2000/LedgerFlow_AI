from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from decimal import Decimal
from django.utils import timezone
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER


def create_styled_paragraph(text, style, color=None, alignment=None):
    """Helper function to create styled paragraphs."""
    if color:
        text = f'<font color="{color}">{text}</font>'
    if alignment:
        text = f'<para align="{alignment}">{text}</para>'
    return Paragraph(text, style)


def format_contact_info(contact_info):
    """Format contact info by replacing newlines with <br/>"""
    if not contact_info:
        return ""
    # Replace any combination of \n, \r\n, or \r with <br/>
    return contact_info.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br/>")


def generate_interest_income_pdf(response, client, interest_transactions, total):
    """Generate a PDF report for interest income transactions."""

    # Create the PDF document
    doc = SimpleDocTemplate(
        response,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    # Container for the 'Flowable' objects
    elements = []

    # Get styles
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.HexColor("#2C3E50"),  # Dark blue-gray
        alignment=TA_CENTER,
    )

    header_info_style = ParagraphStyle(
        "HeaderInfo",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#7F8C8D"),  # Gray
        alignment=TA_CENTER,
        spaceAfter=20,
    )

    contact_style = ParagraphStyle(
        "ContactInfo",
        parent=styles["Normal"],
        fontSize=12,
        leading=18,
        textColor=colors.HexColor("#2C3E50"),  # Dark blue-gray
        alignment=TA_CENTER,
        spaceAfter=30,
    )

    section_header_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#2980B9"),  # Blue
        spaceBefore=20,
        spaceAfter=10,
    )

    account_info_style = ParagraphStyle(
        "AccountInfo",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#34495E"),  # Dark gray
        alignment=TA_LEFT,
        spaceAfter=10,
    )

    # Add title and metadata
    elements.append(create_styled_paragraph("Interest Income Report", title_style))

    # Calculate time frame
    if interest_transactions:
        all_dates = []
        for group in interest_transactions:
            for tx in group["transactions"]:
                all_dates.append(tx["transaction_date"])
        min_date = min(all_dates)
        max_date = max(all_dates)
        time_frame = f"Tax Year {min_date.year}" if min_date.year == max_date.year else f"Tax Years {min_date.year}-{max_date.year}"
    else:
        time_frame = f"Tax Year {timezone.now().year}"

    # Add report metadata (client ID, date, and time frame) in a subtle header
    report_meta = (
        f"Client ID: {client.client_id} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f'Generated: {timezone.now().strftime("%Y-%m-%d %H:%M")} &nbsp;&nbsp;|&nbsp;&nbsp; '
        f"{time_frame}"
    )
    elements.append(create_styled_paragraph(report_meta, header_info_style))

    # Add contact information with proper line breaks
    if client.contact_info:
        formatted_contact = format_contact_info(client.contact_info)
        elements.append(create_styled_paragraph(formatted_contact, contact_style))

    # Process each group of transactions
    for group in interest_transactions:
        # Add group header with account info
        header_text = f'{group["source"]}'
        elements.append(create_styled_paragraph(header_text, section_header_style))

        # Add account information in a clean format
        account_info = []
        if group["account_info"].get("bank"):
            account_info.append(f'Bank: {group["account_info"]["bank"]}')
        if group["account_info"].get("account_number"):
            account_info.append(f'Account: {group["account_info"]["account_number"]}')
        if group["account_info"].get("statement_type"):
            account_info.append(f'Type: {group["account_info"]["statement_type"]}')

        if account_info:
            elements.append(
                create_styled_paragraph(
                    " &nbsp;&nbsp;|&nbsp;&nbsp; ".join(account_info), account_info_style
                )
            )

        # Create transaction table with modern styling
        table_data = [["Date", "Description", "Amount", "Source File"]]

        # Add transactions to table
        for tx in group["transactions"]:
            table_data.append(
                [
                    tx["transaction_date"].strftime("%Y-%m-%d"),
                    tx["description"],
                    f"${tx['amount']:.2f}",
                    tx["statement_file"]["file_name"] or "N/A",
                ]
            )

        # Add subtotal row
        table_data.append(["", "Subtotal", f"${group['subtotal']:.2f}", ""])

        # Create the table with modern styling
        col_widths = [0.15, 0.35, 0.15, 0.35]  # Adjusted proportional widths
        table = Table(
            table_data, repeatRows=1, colWidths=[w * (7 * inch) for w in col_widths]
        )

        # Modern table styling
        table.setStyle(
            TableStyle(
                [
                    # Header row styling
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2980B9")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("TOPPADDING", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    # Data rows
                    ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -2), 9),
                    ("TEXTCOLOR", (0, 1), (-1, -2), colors.HexColor("#2C3E50")),
                    ("TOPPADDING", (0, 1), (-1, -2), 8),
                    ("BOTTOMPADDING", (0, 1), (-1, -2), 8),
                    # Subtotal row
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#2980B9")),
                    ("TOPPADDING", (0, -1), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
                    # Borders
                    ("GRID", (0, 0), (-1, -2), 0.5, colors.HexColor("#BDC3C7")),
                    ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#2980B9")),
                    # Alignment
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("ALIGN", (2, 1), (2, -1), "RIGHT"),  # Amount column right-aligned
                ]
            )
        )

        elements.append(table)
        elements.append(Spacer(1, 20))

    # Add grand total with modern styling
    total_table = Table(
        [["Total Interest Income:", f"${total:.2f}"]], colWidths=[6 * inch, inch]
    )
    total_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                ("ALIGN", (0, 0), (0, 0), "RIGHT"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ]
        )
    )
    elements.append(total_table)

    # Build the PDF
    doc.build(elements)


def format_currency(amount):
    """Helper function to format currency values."""
    if isinstance(amount, (int, float, Decimal)):
        return f"${amount:,.2f}"
    return "N/A"


def generate_donations_pdf(response, client, donation_transactions, total):
    """Generate a PDF report for charitable donations."""

    # Create the PDF document
    doc = SimpleDocTemplate(
        response,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    # Container for the 'Flowable' objects
    elements = []

    # Get styles
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.HexColor("#2C3E50"),  # Dark blue-gray
        alignment=TA_CENTER,
    )

    header_info_style = ParagraphStyle(
        "HeaderInfo",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#7F8C8D"),  # Gray
        alignment=TA_CENTER,
        spaceAfter=20,
    )

    contact_style = ParagraphStyle(
        "ContactInfo",
        parent=styles["Normal"],
        fontSize=12,
        leading=18,
        textColor=colors.HexColor("#2C3E50"),  # Dark blue-gray
        alignment=TA_CENTER,
        spaceAfter=30,
    )

    section_header_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#2980B9"),  # Blue
        spaceBefore=20,
        spaceAfter=10,
    )

    account_info_style = ParagraphStyle(
        "AccountInfo",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#34495E"),  # Dark gray
        alignment=TA_LEFT,
        spaceAfter=10,
    )

    # Add title and metadata
    elements.append(create_styled_paragraph("Charitable Donations Report", title_style))

    # Calculate time frame
    if donation_transactions:
        all_dates = []
        for group in donation_transactions:
            for tx in group["transactions"]:
                all_dates.append(tx["transaction_date"])
        min_date = min(all_dates)
        max_date = max(all_dates)
        time_frame = f"Tax Year {min_date.year}" if min_date.year == max_date.year else f"Tax Years {min_date.year}-{max_date.year}"
    else:
        time_frame = f"Tax Year {timezone.now().year}"

    # Add report metadata (client ID, date, and time frame) in a subtle header
    report_meta = (
        f"Client ID: {client.client_id} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f'Generated: {timezone.now().strftime("%Y-%m-%d %H:%M")} &nbsp;&nbsp;|&nbsp;&nbsp; '
        f"{time_frame}"
    )
    elements.append(create_styled_paragraph(report_meta, header_info_style))

    # Add contact information with proper line breaks
    if client.contact_info:
        formatted_contact = format_contact_info(client.contact_info)
        elements.append(create_styled_paragraph(formatted_contact, contact_style))

    # Process each group of transactions
    for group in donation_transactions:
        # Add group header with account info
        header_text = f'{group["source"]}'
        elements.append(create_styled_paragraph(header_text, section_header_style))

        # Add account information in a clean format
        account_info = []
        if group["account_info"].get("bank"):
            account_info.append(f'Bank: {group["account_info"]["bank"]}')
        if group["account_info"].get("account_number"):
            account_info.append(f'Account: {group["account_info"]["account_number"]}')
        if group["account_info"].get("statement_type"):
            account_info.append(f'Type: {group["account_info"]["statement_type"]}')

        if account_info:
            elements.append(
                create_styled_paragraph(
                    " &nbsp;&nbsp;|&nbsp;&nbsp; ".join(account_info), account_info_style
                )
            )

        # Create transaction table with modern styling
        table_data = [["Date", "Description", "Amount", "Source File"]]

        # Add transactions to table
        for tx in group["transactions"]:
            table_data.append(
                [
                    tx["transaction_date"].strftime("%Y-%m-%d"),
                    tx["description"],
                    f"${tx['amount']:.2f}",
                    tx["statement_file"]["file_name"] or "N/A",
                ]
            )

        # Add subtotal row
        table_data.append(["", "Subtotal", f"${group['subtotal']:.2f}", ""])

        # Create the table with modern styling
        col_widths = [0.15, 0.35, 0.15, 0.35]  # Adjusted proportional widths
        table = Table(
            table_data, repeatRows=1, colWidths=[w * (7 * inch) for w in col_widths]
        )

        # Modern table styling
        table.setStyle(
            TableStyle(
                [
                    # Header row styling
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2980B9")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("TOPPADDING", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    # Data rows
                    ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -2), 9),
                    ("TEXTCOLOR", (0, 1), (-1, -2), colors.HexColor("#2C3E50")),
                    ("TOPPADDING", (0, 1), (-1, -2), 8),
                    ("BOTTOMPADDING", (0, 1), (-1, -2), 8),
                    # Subtotal row
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#2980B9")),
                    ("TOPPADDING", (0, -1), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
                    # Borders
                    ("GRID", (0, 0), (-1, -2), 0.5, colors.HexColor("#BDC3C7")),
                    ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#2980B9")),
                    # Alignment
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("ALIGN", (2, 1), (2, -1), "RIGHT"),  # Amount column right-aligned
                ]
            )
        )

        elements.append(table)
        elements.append(Spacer(1, 20))

    # Add grand total with modern styling
    total_table = Table(
        [["Total Donations:", f"${total:.2f}"]], colWidths=[6 * inch, inch]
    )
    total_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                ("ALIGN", (0, 0), (0, 0), "RIGHT"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ]
        )
    )
    elements.append(total_table)

    # Build the PDF
    doc.build(elements)
