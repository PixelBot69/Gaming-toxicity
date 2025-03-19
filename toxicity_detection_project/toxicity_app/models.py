# toxicity_app/models.py
from django.db import models

class Report(models.Model):
    REPORT_TYPES = [
        (0, 'Hate Speech'),
        (1, 'Offensive Language'),
        (2, 'Not Toxic (False Positive)'),
    ]
    
    message_text = models.TextField()
    report_type = models.IntegerField(choices=REPORT_TYPES)
    reporter_username = models.CharField(max_length=100)
    reported_username = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Report by {self.reporter_username}: {self.message_text[:50]}..."