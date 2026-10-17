
from django.db import models
from django.contrib.auth import get_user_model

class Habit(models.Model):
    owner = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="habits",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    target_per_week = models.PositiveSmallIntegerField(default=7)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "completed"])]
    

  
