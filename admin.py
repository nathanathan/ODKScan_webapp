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
            #Do Processing here:
            import subprocess
            #TODO: Move APP_ROOT?
            APP_ROOT = os.path.dirname(__file__)
            #This blocks
            subprocess.Popen(['touch',
                              'testing_output_location',
                              #obj.image.path,
                              ],
                cwd=os.path.join(APP_ROOT,
                                 'mScan',
                                 'TestSuite'),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE).communicate()
            obj.status = 'p'
            obj.save()
admin.site.register(FormImage, FormImageAdmin)