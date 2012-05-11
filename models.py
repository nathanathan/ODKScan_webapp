from django.db import models
import os

def get_template_path(instance, filename):
    return os.path.join(instance.name, filename)
class Template(models.Model):
    name = models.CharField(max_length=200, unique=True)
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
    ('t', 'Transcribed'),
)
def get_form_image_path(instance, filename):
    import time
    timestamp = str(int(100*time.time()))
    root, ext = os.path.splitext(filename)
    return os.path.join(timestamp, root, "photo" + ext)
class FormImage(models.Model):
    template = models.ForeignKey(Template, blank=True, null=True)
    image = models.ImageField(upload_to=get_form_image_path)
    status = models.CharField(max_length=1, choices=STATUSES)
    error_message = models.TextField(blank=True, null=True)
    upload_time = models.DateTimeField(auto_now=True)
    markedup_image_path = models.FilePathField(blank=True, null=True) #rename output_path
    json_output_path = models.FilePathField(blank=True, null=True) #remove