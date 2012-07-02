from ODKScan_webapp.models import Template, FormImage, LogItem
import ODKScan_webapp.actions as actions
from django.contrib import admin
from django.conf import settings
import os, sys

#from django.db import models
#from form_utils.widgets import ImageWidget
#from ODKScan_webapp.widgets import AdminImageWidget



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
    list_filter = ('upload_time', 'status', 'template')
    fields = ('image', 'template', 'error_message',)
    readonly_fields = ('error_message',) #TODO: Only display error if it exists
    #formfield_overrides = { models.ImageField: {'widget': AdminImageWidget}}
    actions = [actions.process_forms,
               actions.transcribe,
               actions.transcribeNoImages,
               actions.transcribeNoAutofill,
               actions.transcribeNoEverything,
               actions.transcribeFormView,
               actions.finalize,
               actions.generate_csv]

    def filename(self, obj):
        return os.path.split(obj.image.name)[1]
    
    def save_model(self, request, obj, form, change):
        obj.user = request.user
        obj.save()
admin.site.register(FormImage, FormImageAdmin)

class LogItemAdmin(admin.ModelAdmin):
    pass
admin.site.register(LogItem, LogItemAdmin)

