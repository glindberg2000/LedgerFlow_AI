from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import BusinessProfile, Transaction


@login_required
def profile_view(request):
    business_profile = BusinessProfile.objects.filter(user=request.user).first()
    transactions = Transaction.objects.filter(business=business_profile).order_by(
        "-created_at"
    )

    context = {
        "business_profile": business_profile,
        "transactions": transactions,
    }
    return render(request, "profiles/profile.html", context)
