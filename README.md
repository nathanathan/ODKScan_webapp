ODKScan_webapp
==============

A Django app that runs ODKScan

Istallation
===========

Setup ODKScan-core in this directory (see: https://github.com/nathanathan/ODKScan-core)

Enable the django admin site

In settings.py:

* Give values to MEDIA_ROOT and MEDIA_URL
* Add "ODKScan_webapp" to INSTALLED_APPS

In urls.py:

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
	
Architecture
============

This app is based on the django admin site. You can read about how it is set up in the django tutorial here:

https://docs.djangoproject.com/en/1.4/intro/tutorial01/

Most of the relevant django code is in admin.py and models.py

There are a few idiosyncratic parts:

* When images are uploaded they are processed by ODKScan.
* The transcription interface.
* The template editor.