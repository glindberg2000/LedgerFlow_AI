from django.db import models
from django.contrib.auth.models import User


class BusinessProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    business_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "profiles"

    def __str__(self):
        return self.business_name


class Transaction(models.Model):
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "profiles"

    def __str__(self):
        return f"{self.business.business_name} - {self.amount}"
