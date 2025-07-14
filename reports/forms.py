from django import forms
from profiles.models import TaxYear


class BinderSelectForm(forms.Form):
    binder = forms.ModelChoiceField(
        queryset=TaxYear.objects.select_related("business_profile").order_by("-year"),
        required=True,
        label="Binder (Company – Year)",
        to_field_name="id",
        widget=forms.Select(attrs={"style": "width: 350px;"}),
    )

    # Optionally override label_from_instance for better display
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["binder"].label_from_instance = (
            lambda obj: f"{obj.business_profile.company_name} – {obj.year}"
        )
