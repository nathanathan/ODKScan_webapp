ODKScan_webapp
==============

A Django app interface for ODK Scan

Installation
===========

[Get the django admin site running.](https://docs.djangoproject.com/en/1.4/intro/tutorial01/)

Now in your django app directory run:

```bash
git clone git://github.com/UW-ICTD/ODKScan_webapp.git --recursive
#If this was forked you might need to alter the UW-ICTD part.
```

In settings.py:

* Give values to MEDIA_ROOT and MEDIA_URL (e.g. "/media/")
* Add "ODKScan_webapp" to INSTALLED_APPS

Paste this at the bottom of urls.py:

```python
urlpatterns += [url(r'', include('ODKScan_webapp.urls'))]

#This to serve static media. For production servers you aren't supposed to serve media with Django.
from django.conf import settings
if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }),
   )

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()
```

Check to see if the ODKScan_webapp appears on your django admin page.

If that worked, go through [the ODKScan-core readme](https://github.com/UW-ICTD/ODKScan-core/blob/master/README.md) to get the image processing working.

Architecture
============

* The django code in admin.py and models.py configures what's in the admin interface.
* actions.py contains code for processing forms with ODK Scan, rendering transcription pages and generating csvs.

