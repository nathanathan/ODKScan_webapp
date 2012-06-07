from django.db import models
import os

#TODO: At the moment templates (and maybe form images) can only be saved once.
#        because django doesn't overwrite or delete the previous versions.
def get_template_path(instance, filename):
    root, ext = os.path.splitext(filename)
    if(ext == '.json'):
        return os.path.join(instance.name, 'template' + ext)
    else:
        return os.path.join(instance.name, 'form' + ext)
class Template(models.Model):
    name = models.CharField(max_length=200, unique=True)
    #Make json a text input?
    json = models.FileField(upload_to=get_template_path)
    image = models.ImageField(upload_to=get_template_path)
    #These functions make it so that in the foreign key selector the name of the template is shown.
    def __str__(self):
        return self.__unicode__()
    def __unicode__(self):
        return self.name

STATUSES = (
    ('e', 'Error'),
    ('p', 'Processed'),
    ('m', 'Modified'),
    ('f', 'Finalized'),
)
def get_form_image_path(instance, filename):
    import time
    output_dir = str(int(100*time.time()))
    root, ext = os.path.splitext(filename)
    return os.path.join(output_dir, 'photo', filename)
class FormImage(models.Model):
    template = models.ForeignKey(Template, blank=True, null=True)
    image = models.ImageField(upload_to=get_form_image_path)
    status = models.CharField(max_length=1, choices=STATUSES)
    error_message = models.TextField(blank=True, null=True)
    upload_time = models.DateTimeField(auto_now=True)
    def _get_output_path(self):
        return os.path.dirname(os.path.dirname(self.image.path))
    output_path = property(_get_output_path)