from ODKScan_webapp.models import Template, FormImage, LogItem
import ODKScan_webapp.actions as actions
from django.contrib import admin
from django.conf import settings
import os, sys


from django.utils.translation import ugettext_lazy as _
from django.contrib.admin import SimpleListFilter

class CompleteFilter(SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('Transcribed')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'transcribed'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('transcribed', _('transcribed')),
            ('untranscribed', _('untranscribed')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        ##This function is really terrible code by the way, and for any amount of scaling should be redone
        def isTranscribed(form_image):
            json_path = os.path.join(form_image.output_path, 'users', str(request.user), 'output.json')
            return os.path.exists(json_path)
        if self.value() == 'transcribed':
            return queryset.filter(pk__in=[x.pk for x in list(queryset) if isTranscribed(x)])
        if self.value() == 'untranscribed':
            return queryset.exclude(pk__in=[x.pk for x in list(queryset) if isTranscribed(x)])


class FormImageInline(admin.TabularInline):
    fields = ('image', 'template',)
    model = FormImage

class TemplateAdmin(admin.ModelAdmin):
    fields = ('name', 'json', 'image',)
    list_display = ('name',)
    inlines = [FormImageInline]
    
admin.site.register(Template, TemplateAdmin)

class FormImageAdmin(admin.ModelAdmin):
    list_display = ['filename', 'upload_time', 'status',]
    list_filter = (CompleteFilter, 'status', 'template', 'batch', )#'upload_time', 
    fields = ('image', 'template', 'batch', 'processing_log', )
    readonly_fields = ('processing_log',)
    actions = [actions.process_forms,
               actions.transcribe,
               #actions.transcribeFormView,
               actions.finalize,
               actions.generate_csv]

    def filename(self, obj):
        return os.path.split(obj.image.name)[1]
    
    def save_model(self, request, obj, form, change):
        obj.user = request.user
        obj.save()
admin.site.register(FormImage, FormImageAdmin)

class LogItemAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'formImage',]
    list_filter = ('timestamp', 'user', 'formImage',)
admin.site.register(LogItem, LogItemAdmin)


