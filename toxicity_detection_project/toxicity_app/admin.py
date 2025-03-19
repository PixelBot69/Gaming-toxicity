# toxicity_app/admin.py
from django.contrib import admin
from django.http import HttpResponse
import csv
from .models import Report

class ReportAdmin(admin.ModelAdmin):
    list_display = ('reporter_username', 'reported_username', 'report_type_display', 'timestamp', 'message_preview')
    list_filter = ('report_type', 'timestamp')
    search_fields = ('message_text', 'reporter_username', 'reported_username')
    actions = ['export_as_csv']
    
    def report_type_display(self, obj):
        return dict(Report.REPORT_TYPES)[obj.report_type]
    report_type_display.short_description = 'Report Type'
    
    def message_preview(self, obj):
        return obj.message_text[:50] + '...' if len(obj.message_text) > 50 else obj.message_text
    message_preview.short_description = 'Message'
    
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=toxicity_reports.csv'
        writer = csv.writer(response)
        
        # Write header row with human-readable report type
        header_row = field_names.copy()
        header_row.append('report_type_display')  # Add human-readable report type
        writer.writerow(header_row)
        
        # Write data rows
        for obj in queryset:
            row = [getattr(obj, field) for field in field_names]
            row.append(dict(Report.REPORT_TYPES)[obj.report_type])  # Add human-readable report type
            writer.writerow(row)
        
        return response
    export_as_csv.short_description = "Export selected reports as CSV"

admin.site.register(Report, ReportAdmin)