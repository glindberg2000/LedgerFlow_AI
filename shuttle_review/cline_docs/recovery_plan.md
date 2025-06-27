# LedgerFlow Recovery Plan

## Introduction

This document outlines the precise steps required to fix the critical bugs currently plaguing the reports section of the LedgerFlow application. The previous attempts to resolve these issues were catastrophic failures, resulting in a broken and inconsistent user experience. This plan provides a clear, actionable path to full recovery.

Follow these steps exactly to restore functionality.

## Issue 1: PDF Download Crash for Interest Income Report

**Problem:** When clicking the "Download PDF" link on the Interest Income report, the application crashes with an `AttributeError: 'NoneType' object has no attribute 'has_header'`. This is because the function responsible for generating the PDF (`generate_interest_income_pdf`) does not return an HTTP response object as required.

**Solution:**

1.  Open the file `reports/pdf_utils.py`.
2.  Locate the `generate_interest_income_pdf` function.
3.  Add `return response` as the very last line of the function.

**Verification:** After this change, the PDF download for the Interest Income report will work correctly.

## Issue 2: Donations Report Shows 0 Rows

**Problem:** The Donations Report is not finding any transactions, even though they exist for the selected client. This is due to an incorrect database query in the `donations_report` view. The field lookup used to filter by client is wrong.

**Solution:**

1.  Open the file `reports/views.py`.
2.  Locate the `donations_report` function.
3.  The current query is attempting to filter using `statement_file__client__client_id`. While this seems logical, it is not working as expected. To fix this, we will use a more direct and robust query that filters on the `client` foreign key directly.
4.  Replace the existing `Transaction.objects.filter(...)` call with the following corrected query:

    ```python
    donation_txs = Transaction.objects.filter(
        statement_file__client=client
    ).filter(
        Q(description__icontains="DONATION") |
        Q(description__icontains="CHARITABLE") |
        Q(category__icontains="donation") |
        Q(category__icontains="charitable") |
        Q(description__iregex=r'\\b(GIVE|FUND|FOUNDATION)\\b')
    ).order_by('transaction_date').select_related('statement_file')
    ```

**Verification:** The Donations Report will now correctly display all relevant transactions for the selected client. 