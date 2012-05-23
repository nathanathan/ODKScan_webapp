from ODKScan_webapp.models import Template, FormImage
from django.contrib import admin
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
import os, sys
from django.db import models
#from form_utils.widgets import ImageWidget
#from ODKScan_webapp.widgets import AdminImageWidget

from django.template import RequestContext, loader
from django.http import HttpResponse

def process_json_output(pyobj):
    """
    Modifies segment image paths and sizes so it is easy to use them in the transcribe.html template.
    """
    for field in pyobj['fields']:
        for segment in field['segments']:
            #Modify path
            image_path = segment.get('image_path')
            if not image_path: continue
            segment['image_path'] = "/media" + image_path.split("media")[1]
            #Modify image size
            dpi = 100 #A guess for dots per inch
            segment_width = segment.get("segment_width", field.get("segment_width", pyobj.get("segment_width")))
            segment_height = segment.get("segment_height", field.get("segment_height", pyobj.get("segment_height")))
            if not segment_width or not segment_height: continue
            segment['width_inches'] = float(segment_width) / dpi
            segment['height_inches'] = float(segment_height) / dpi
    return pyobj

#Put under views?
def transcribe(modeladmin, request, queryset):
    selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
    ct = ContentType.objects.get_for_model(queryset.model)
    #return HttpResponseRedirect("/transcribe/?ct=%s&ids=%s" % (ct.pk, ",".join(selected)))
    import json, codecs
    import sys
    form_template = None
    json_outputs = []
    for formImage in queryset:
        json_path = os.path.join(formImage.output_path, 'output.json')
        if not os.path.exists(json_path):
            continue
        if form_template is None:
            form_template = formImage.template
        elif form_template.name != formImage.template.name:
            raise Exception("Mixed templates: " + form_template.name + " and " + formImage.template.name)
        fp = codecs.open(json_path, mode="r", encoding="utf-8")
        pyobj = json.load(fp, encoding='utf-8')
        pyobj['formImage'] = formImage
        process_json_output(pyobj)
        json_outputs.append(pyobj)
        #print >>sys.stderr, json.dumps(pyobj, ensure_ascii=False, indent=4)
    if form_template is None:
        raise Exception("no template")
    form_template_fp = codecs.open(form_template.json.path, mode="r", encoding="utf-8")
    json_template = json.load(form_template_fp, encoding='utf-8')
    t = loader.get_template('transcribe.html')
    c = RequestContext(request, {
                 'json_template':json_template,
                 'json_outputs':json_outputs,
                 })
    return HttpResponse(t.render(c))
transcribe.short_description = "Transcribe selected forms."

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
    actions = [transcribe]

    def filename(self, obj):
        return os.path.split(obj.image.name)[1]
    
    def save_model(self, request, obj, form, change):
        obj.user = request.user
        obj.save()
        #Does image processing:
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
        obj.error_message = stderrdata
        json_path = os.path.join(obj.output_path, 'output.json')
        if os.path.exists(json_path):
            obj.status = 'p'
        else:
            obj.status = 'e'
        obj.save()
        
admin.site.register(FormImage, FormImageAdmin)