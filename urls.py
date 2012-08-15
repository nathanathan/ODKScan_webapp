from django.conf.urls.defaults import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

import os
APP_NAME = os.path.split(os.path.dirname(__file__))[-1]
#Try __package__
urlpatterns = patterns(APP_NAME,
    url(r'^save_transcription', 'views.save_transcriptions'),
    url(r'^formView', 'views.form_view'),
    url(r'^fieldView', 'views.field_view'),
    
    url(r'^upload_template', 'views.upload_template'),
    url(r'^upload_form', 'views.upload_form'),
    url(r'^test_template', 'views.test_template'),
    
    url(r'^log', 'views.log'),
    
    #Functions for importing android data and doing some preprocessing
    url(r'^parseSaveLogItems', 'analysis.parseSaveLogItems'),
    url(r'^importAndroidData', 'analysis.importAndroidData'),
    url(r'^generateAndroidOutput', 'analysis.generateAndroidOutput'),
    url(r'^correct_transcriptions', 'analysis.correct_transcriptions'),
    url(r'^fillUserFormCondition', 'analysis.fillUserFormCondition'),
    url(r'^full_pipeline', 'analysis.full_pipeline'),
    
    #Data views
    url(r'^analyseTarget/(?P<userName>\w*)/(?P<formName>\w*)', 'analysis.analyse_target'),
    url(r'^analyse', 'analysis.analyse'),
)