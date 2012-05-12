from ODKScan_webapp.models import Template, FormImage
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
import os
from django.db import models
#from form_utils.widgets import ImageWidget
#from ODKScan_webapp.widgets import AdminImageWidget

from django.template import Context, loader
from django.http import HttpResponse

def process_json_output(pyobj):
    """
    Modifies a json python object so imagePaths so they work as links
    and each field has a value property.
    """
    for field in pyobj['fields']:
        field['value'] = field.get('value', 'value')
        for segment in field['segments']:
            segment['imagePath'] = "/media" + segment['imagePath'].split("media")[1]
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
        json_path = os.path.join(formImage.markedup_image_path, 'output.json')
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
    c = Context({
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
    fields = ('image', 'template', 'markedup_image_path', 'error_message',)
    readonly_fields = ('markedup_image_path', 'error_message',)
    #formfield_overrides = { models.ImageField: {'widget': AdminImageWidget}}
    actions = [transcribe]

    def filename(self, obj):
        return obj.image.name
    
    def save_model(self, request, obj, form, change):
        obj.user = request.user
        obj.save()
        #Does image processing:
        import subprocess
        #TODO: Move APP_ROOT?
        APP_ROOT = os.path.dirname(__file__)
        obj.markedup_image_path = os.path.dirname(obj.image.path)
        #This blocks, for scaling we should add a "processing" status and do it asyncronously.
        stdoutdata, stderrdata = subprocess.Popen(['./ODKScan.run',
                          'assets/form_templates/example',
                          obj.image.path,
                          obj.markedup_image_path
                          ],
            cwd=os.path.join(APP_ROOT,
                             'ODKScan-core'),
            env={'LD_LIBRARY_PATH':'/usr/local/lib'},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE).communicate()
        if(len(stderrdata) == 0):
            obj.status = 'p'
        else:
            obj.status = 'e'
            obj.error_message = stderrdata
        obj.save()
        
admin.site.register(FormImage, FormImageAdmin)