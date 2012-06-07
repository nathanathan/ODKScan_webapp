from ODKScan_webapp.models import Template, FormImage
from ODKScan_webapp.actions import transcribe, finalize, generate_csv
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
    actions = [transcribe, finalize, generate_csv]

    def filename(self, obj):
        return os.path.split(obj.image.name)[1]
    
    def save_model(self, request, obj, form, change):
        obj.user = request.user
        obj.save()
        #This is where wee make the call to ODKScan core
        import subprocess
        #TODO: Move APP_ROOT?
        APP_ROOT = os.path.dirname(__file__)
        #print >>sys.stderr, obj.output_path
        #This blocks, for scaling we should add a "processing" status and do it asyncronously.
        stdoutdata, stderrdata = subprocess.Popen(['./ODKScan.run',
                          os.path.dirname(obj.template.image.path) + '/',
                          obj.image.path,
                          obj.output_path
                          ],
            cwd=os.path.join(APP_ROOT,
                             'ODKScan-core'),
            env={'LD_LIBRARY_PATH':'/usr/local/lib'}, #TODO: This could cause problems on other systems, document or fix
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE).communicate()
        print >>sys.stdout, stdoutdata
        obj.error_message = stderrdata
        json_path = os.path.join(obj.output_path, 'output.json')
        if os.path.exists(json_path):
            obj.status = 'p'
        else:
            obj.status = 'e'
        obj.save()
        
admin.site.register(FormImage, FormImageAdmin)