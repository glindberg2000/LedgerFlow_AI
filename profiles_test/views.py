from django.shortcuts import render, redirect
from django.contrib import messages
import csv
from .forms import TransactionCSVForm, StatementFileUploadForm

# from .models import (
#     Transaction,
#     BusinessProfile,
#     UploadedFile,
#     CLASSIFICATION_METHOD_UNCLASSIFIED,
#     PAYEE_EXTRACTION_METHOD_UNPROCESSED,
# )
import logging
from django.views.generic import ListView
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from .utils import sync_transaction_id_sequence

logger = logging.getLogger(__name__)

# Create your views here.


def upload_transactions(request):
    if request.method == "POST":
        sync_transaction_id_sequence()
        form = TransactionCSVForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode("utf-8").splitlines()
            reader = csv.DictReader(decoded_file)
            client = BusinessProfile.objects.get(client_id="Tim and Gene")
            for row in reader:
                try:
                    Transaction.objects.create(
                        client=client,
                        transaction_date=row["transaction_date"],
                        description=row["description"],
                        amount=row["amount"],
                        file_path=row["file_path"],
                        source=row["source"],
                        transaction_type=row["transaction_type"],
                        normalized_amount=row["normalized_amount"],
                        statement_start_date=row["statement_start_date"] or None,
                        statement_end_date=row["statement_end_date"] or None,
                        account_number=row["account_number"],
                        transaction_id=row["transaction_id"],
                        classification_method=CLASSIFICATION_METHOD_UNCLASSIFIED,
                        payee_extraction_method=PAYEE_EXTRACTION_METHOD_UNPROCESSED,
                        needs_account_number=(
                            not row.get("account_number")
                            or str(row.get("account_number")).strip() == ""
                        ),
                    )
                except Exception as e:
                    logger.error(f"Error processing row {row}: {e}")
                    messages.error(request, f"Error processing row: {row}")
            messages.success(request, "Transactions uploaded successfully.")
            return redirect("profile-list")
    else:
        form = TransactionCSVForm()
    return render(request, "profiles/upload_transactions.html", {"form": form})


class BusinessProfileListView(ListView):
    model = BusinessProfile
    template_name = "profiles/profile_list.html"
    context_object_name = "profiles"


def upload_statement_files(request):
    if request.method == "POST":
        form = StatementFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            client = form.cleaned_data["client"]
            file_type = form.cleaned_data["file_type"]
            files = request.FILES.getlist("files")
            uploaded_by = request.user if request.user.is_authenticated else None
            success, errors = [], []
            for f in files:
                try:
                    # instance = UploadedFile.objects.create(
                    #     client=client,
                    #     file=f,
                    #     file_type=file_type,
                    #     original_filename=f.name,
                    #     uploaded_by=uploaded_by,
                    #     status="uploaded",
                    # )
                    success.append(f"Uploaded: {f.name}")
                except (IntegrityError, ValidationError) as e:
                    # Check for duplicate error
                    if "unique_client_statement_hash" in str(e):
                        msg = f"{f.name}: This statement file has already been uploaded for this client."
                    else:
                        msg = f"{f.name}: {e}"
                    logger.error(f"Error uploading {f.name}: {e}")
                    errors.append(msg)
                except Exception as e:
                    logger.error(f"Error uploading {f.name}: {e}")
                    errors.append(f"{f.name}: {e}")
            if success:
                messages.success(request, " ".join(success))
            if errors:
                messages.error(request, " ".join(errors))
                # Do NOT redirect if there are errors; re-render the form so the message shows
                return render(
                    request, "profiles/upload_statement_files.html", {"form": form}
                )
            # Only redirect if all files were successful
            return redirect("upload-statement-files")
    else:
        form = StatementFileUploadForm()
    return render(request, "profiles/upload_statement_files.html", {"form": form})
