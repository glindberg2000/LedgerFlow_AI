from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import OrganizerWorkbook, OrganizerOutput
from .forms import OrganizerWorkbookForm


@login_required
def upload_workbook(request):
    if request.method == "POST":
        form = OrganizerWorkbookForm(request.POST, request.FILES)
        if form.is_valid():
            workbook = form.save()
            messages.success(request, "Workbook uploaded and queued for processing.")
            return redirect("organizer_workbook_detail", pk=workbook.id)
    else:
        form = OrganizerWorkbookForm()
    return render(request, "organizers/upload.html", {"form": form})


@login_required
def workbook_detail(request, pk):
    workbook = get_object_or_404(OrganizerWorkbook, pk=pk)
    outputs = workbook.outputs.all().order_by("output_type", "page_number")
    return render(
        request, "organizers/detail.html", {"workbook": workbook, "outputs": outputs}
    )
