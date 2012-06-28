ODKScan_webapp
==============

A Django app interface for ODK Scan

Installation
===========

[Get the django admin site running.](https://docs.djangoproject.com/en/1.4/intro/tutorial01/)

Now in your django app directory run:

	git clone git://github.com/nathanathan/ODKScan_webapp.git --recursive
	#If this was forked you might need to alter the nathanathan part.

In settings.py:

* Give values to MEDIA_ROOT and MEDIA_URL (e.g. "/media/")
* Add "ODKScan_webapp" to INSTALLED_APPS

Paste this at the bottom of urls.py:

	#This to serve static media. For production servers you aren't supposed to serve media with Django.
	from django.conf import settings
	if settings.DEBUG:
	    urlpatterns += patterns('',
	        url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {
	            'document_root': settings.MEDIA_ROOT,
	        }),
	   )
	
	#This is for serving static files:
	from django.contrib.staticfiles.urls import staticfiles_urlpatterns
	urlpatterns += staticfiles_urlpatterns()
	urlpatterns += [url(r'^save_transcription', 'ODKScan_webapp.views.save_transcriptions')]

Check to see if the ODKScan_webapp appears on your django admin page.

If that worked, go through [the ODKScan-core readme](https://github.com/nathanathan/ODKScan-core/blob/master/README.md) to get the image processing working.

Architecture
============

Most of the relevant django code is in admin.py and models.py

There are a few idiosyncratic parts:

* When images are uploaded they are processed by ODKScan-core.
* The transcription interface.
* The template editor.