
from django.db import models


class Medicine(models.Model):
    """Master catalog entry for a dispensary medicine."""

    class Category(models.TextChoices):
        GENERAL = 'general', 'General'
        ANALGESIC = 'analgesic', 'Analgesic'
        ANTIBIOTIC = 'antibiotic', 'Antibiotic'
        SUPPLEMENT = 'supplement', 'Supplement'
        FIRST_AID = 'first_aid', 'First Aid'

    class Unit(models.TextChoices):
        TABLET = 'tablet', 'Tablet'
        STRIP = 'strip', 'Strip'
        BOTTLE = 'bottle', 'Bottle'
        BOX = 'box', 'Box'
        TUBE = 'tube', 'Tube'

    name = models.CharField(max_length=120, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.GENERAL)
    unit = models.CharField(max_length=20, choices=Unit.choices, default=Unit.TABLET)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = 'Medicine'
        verbose_name_plural = 'Medicines'


class Stock(models.Model):
    """Live stock count for a catalogued medicine."""

    class SeasonTag(models.TextChoices):
        GENERAL = 'general', 'General'
        SUMMER = 'summer', 'Summer'
        MONSOON = 'monsoon', 'Monsoon'
        WINTER = 'winter', 'Winter'

    medicine = models.OneToOneField(Medicine, on_delete=models.CASCADE, related_name='stock')
    quantity = models.PositiveIntegerField(default=0)
    season_tag = models.CharField(max_length=20, choices=SeasonTag.choices, default=SeasonTag.GENERAL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.medicine.name} ({self.quantity})'

    class Meta:
        ordering = ['quantity', 'medicine__name']
        verbose_name = 'Stock'
        verbose_name_plural = 'Stock'
