from ODKScan_webapp.models import Template, FormImage
import ODKScan_webapp.actions as actions
from django.contrib import admin
from django.conf import settings
import os, sys

#from django.db import models
#from form_utils.widgets import ImageWidget
#from ODKScan_webapp.widgets import AdminImageWidget


def process_json_output(filepath):
    """
    Modifies segment image paths and sizes so it is easy to use them in the transcribe.html template.
    """
    import json, codecs
    fp = codecs.open(filepath, mode="r", encoding="utf-8")
    pyobj = json.load(fp, encoding='utf-8')#This is where we load the json output
    for field in pyobj['fields']:
        for segment in field['segments']:
            #Modify path
            image_path = segment.get('image_path')
            if not image_path: continue
            segment['name'] = os.path.basename(image_path.split("media")[1]).split(".jpg")[0]
            #Modify image size
            dpi = 100.0 #A guess for dots per inch
            segment_width = segment.get("segment_width", field.get("segment_width", pyobj.get("segment_width")))
            segment_height = segment.get("segment_height", field.get("segment_height", pyobj.get("segment_height")))
            if not segment_width or not segment_height: continue
            #segment['width_inches'] = float(segment_width) / dpi
            #segment['height_inches'] = float(segment_height) / dpi
    return pyobj


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
    actions = [actions.transcribe, actions.transcribeNoImages, actions.transcribeNoAutofill, actions.transcribeFormView, actions.finalize, actions.generate_csv]

    def filename(self, obj):
        return os.path.split(obj.image.name)[1]
    
    def save_model(self, request, obj, form, change):
        obj.user = request.user
        obj.save()
        #This is where we make the call to ODKScan core
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
            process_json_output()
            obj.status = 'p'
        else:
            obj.status = 'e'
        obj.save()
        
admin.site.register(FormImage, FormImageAdmin)