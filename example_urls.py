from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'djangotest.views.home', name='home'),
    # url(r'^djangotest/', include('djangotest.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    
    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

#Not supposed to do this in a production server
from django.conf import settings
if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }),
   )

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()

urlpatterns += [url(r'^save_transcription', 'ODKScan_webapp.views.save_transcriptions')]
urlpatterns += [url(r'^formView', 'ODKScan_webapp.views.form_view')]
urlpatterns += [url(r'^fieldView', 'ODKScan_webapp.views.field_view')]
urlpatterns += [url(r'^log', 'ODKScan_webapp.views.log')]

#Functions for importing android data and doing some preprocessing
urlpatterns += [url(r'^parseSaveLogItems', 'ODKScan_webapp.analysis.parseSaveLogItems')]
urlpatterns += [url(r'^importAndroidData', 'ODKScan_webapp.analysis.importAndroidData')]
urlpatterns += [url(r'^generateAndroidOutput', 'ODKScan_webapp.analysis.generateAndroidOutput')]
urlpatterns += [url(r'^correct_transcriptions', 'ODKScan_webapp.analysis.correct_transcriptions')]
urlpatterns += [url(r'^fillUserFormCondition', 'ODKScan_webapp.analysis.fillUserFormCondition')]
urlpatterns += [url(r'^full_pipeline', 'ODKScan_webapp.analysis.full_pipeline')]

#Data views
urlpatterns += [url(r'^analyseTarget/(?P<userName>\w*)/(?P<formName>\w*)', 'ODKScan_webapp.analysis.analyse_target')]
urlpatterns += [url(r'^analyse', 'ODKScan_webapp.analysis.analyse')]
