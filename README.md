ODKScan_webapp
==============

Istallation:

Install mScan:

git clone git://github.com/villagereach/mScan.git

Enable the django admin site

In settings.py:

Give values to MEDIA_ROOT and MEDIA_URL
Add ODKScan_webapp to INSTALLED_APPS

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