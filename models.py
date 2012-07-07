from django.db import models
from django.contrib.auth.models import User
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
#    def save(self, *args, **kwargs):
#        if self.pk is None:
#            #This is being changed
#            self.json
#        super(Model, self).save(*args, **kwargs)

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
    def __str__(self):
        return self.__unicode__()
    def __unicode__(self):
        return os.path.splitext(os.path.basename(self.image.name))[0]
    
#For logging:
class LogItem(models.Model):
    user = models.ForeignKey(User, blank=True, null=True)
    url = models.CharField(max_length=1000, null=True)#Just to be sure nothing gets left out.
    formImage = models.ForeignKey(FormImage, null=True)
    view = models.CharField(max_length=200, null=True)
    fieldName = models.CharField(max_length=200, null=True)
    previousValue = models.CharField(max_length=200, null=True)
    newValue = models.CharField(max_length=200, null=True)
    activity = models.CharField(max_length=200, null=True)
    forms = models.CharField(max_length=200, null=True)
    segment = models.CharField(max_length=200, null=True)
    timestamp = models.DateTimeField(auto_now=True, null=True)

LOCATIONS = (
    ('s', 'Seattle'),
    ('i', 'India'),
)

class UserProfile(models.Model):
    user = models.OneToOneField(User, primary_key=True)
    age = models.IntegerField(null=True, blank=True)
    GENDERS = (
        ('m', 'Male'),
        ('f', 'Female'),
    )
    gender = models.CharField(max_length=1, choices=GENDERS,
                              null=True, blank=True)
    COMPUTER_TIMES = (
        ('a', 'Less than 6 months'),
        ('b', 'About 1 year'),
        ('c', '2-3 years'),
        ('d', '3-5 years'),
        ('e', '5-10 years'),
        ('f', '10 or more years'),
    )
    computer_experience = models.CharField(max_length=1,
                                           choices=COMPUTER_TIMES,
                                           verbose_name='How long have you been using a computer?',
                                           null=True, blank=True)
    COMPUTER_USAGES = (
        ('a', 'Less than 2 hours per week'),
        ('b', '2-5 hours per week'),
        ('c', '6-10 hours per week'),
        ('d', '11-20 hours per week'),
        ('e', '21 or more hours per week'),
    )
    average_computer_use = models.CharField(max_length=1,
                                            choices=COMPUTER_USAGES,
                                            verbose_name='On average, how many hours per week do you use your computer?',
                                            help_text='(If you are having trouble thinking of an average, think back over the last two weeks.',
                                            null=True, blank=True)
    LEVELS = (
        ('Beginner', (
                (1, 1),
            )
        ),
        ('Intermediate', (
                (2, 2),
                (3, 3),
                (4, 4),
            )
        ),
        ('Expert', (
                (5, 5),
            )
         ),
    )
    user_level = models.IntegerField(choices=LEVELS,
                                     verbose_name='What level of computer user would you say that you are?',
                                     null=True, blank=True)
    typing_level = models.IntegerField(choices=LEVELS,
                                       verbose_name='What would you say is your typing proficiency on computer?',
                                       null=True, blank=True)
    use_smart_phone = models.NullBooleanField(verbose_name='Do you use a smartphone?')
    use_tablet = models.NullBooleanField(verbose_name='Do you use a tablet?')
    use_media_player = models.NullBooleanField(verbose_name='Do you use a media player?')
    use_other = models.NullBooleanField(verbose_name='Do you use a touchscreen device outside of the categories above?')
    touch_screen_time = models.CharField(max_length=1,
                               choices=COMPUTER_TIMES,
                               verbose_name='How long have you been using a touchscreen device?',
                               null=True, blank=True)
    touch_screen_typing_level = models.IntegerField(choices=LEVELS,
                                       verbose_name='What would you say is your typing proficiency on a touchscreen mobile device?',
                                       null=True, blank=True)
    no_like = models.TextField(verbose_name='Which of the data entry techniques in this study did you NOT like? Why?',
                               null=True, blank=True)
    other_comments = models.TextField(null=True, blank=True)
    location = models.CharField(max_length=1, choices=LOCATIONS)
