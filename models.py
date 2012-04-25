from django.db import models
import os

def get_path(instance, filename):
    return os.path.join(instance.name, filename)

class Template(models.Model):
    name = models.CharField(max_length=200, unique=True)
    json = models.FileField(upload_to=get_path)
    image = models.ImageField(upload_to=get_path)

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
class FormImage(models.Model):
    template = models.ForeignKey(Template, blank=True, null=True)
    image = models.ImageField(upload_to='%Y%j%h%M%s')
    status = models.CharField(max_length=1, choices=STATUSES)
    upload_time = models.DateTimeField(auto_now=True)
