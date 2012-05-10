from ODKScan_webapp.models import Template, FormImage
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
import os

def transcribe(modeladmin, request, queryset):
    selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
    ct = ContentType.objects.get_for_model(queryset.model)
    return HttpResponseRedirect("/export/?ct=%s&ids=%s" % (ct.pk, ",".join(selected)))
transcribe.short_description = "Transcribe selected forms."

class FormImageInline(admin.TabularInline):
    fields = ('image', 'template')
    model = FormImage

class TemplateAdmin(admin.ModelAdmin):
    fields = ('name', 'json', 'image')
    list_display = ('name',)
    inlines = [FormImageInline]
admin.site.register(Template, TemplateAdmin)

class FormImageAdmin(admin.ModelAdmin):
    list_display = ['filename', 'upload_time', 'status']
    list_filter = ('upload_time', 'status')
    fields = ('image', 'template')
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
            #This blocks, for scaling we should add a "processing" status and do it asyncronously.
            stdoutdata, stderrdata = subprocess.Popen(['./ODKScan.run',
                              'assets/form_templates/example',
                              obj.image.path,
                              '../img0'#TODO: How to orgainize output?
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
            obj.save()
            #Debug output
            import sys
            print >>sys.stderr, '['+stderrdata+']'
admin.site.register(FormImage, FormImageAdmin)