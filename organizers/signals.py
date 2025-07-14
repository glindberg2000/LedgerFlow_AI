from django.db.models.signals import pre_delete
from django.dispatch import receiver
from organizers.models import OrganizerWorkbook
from profiles.models import BinderItem


@receiver(pre_delete, sender=OrganizerWorkbook)
def delete_binderitems_for_organizer(sender, instance, **kwargs):
    BinderItem.objects.filter(organizer_workbook=instance).delete()
