from django.db import models

# Create your models here.
class ContactMessage(models.Model):
    name       = models.CharField(max_length=100)
    email      = models.EmailField()
    message    = models.TextField()
    timestamp  = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True) 

    def __str__(self):
        return f"Message from {self.name} ({self.email})"
