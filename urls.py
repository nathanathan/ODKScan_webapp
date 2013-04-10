from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.views.generic.simple import redirect_to

import os
APP_NAME = os.path.split(os.path.dirname(__file__))[-1]
#Try __package__
urlpatterns = patterns(APP_NAME,
    (r'^$', TemplateView.as_view(template_name='index.html')),
    url(r'^save_transcription', 'views.save_transcriptions'),
    (r'^fieldView', login_required(TemplateView.as_view(template_name='fieldView.html'))),
    (r'^formView', login_required(TemplateView.as_view(template_name='formView.html'))),
    
    #Handlers for testing templates in the template maker.
    url(r'^upload_template', 'template_testing.upload_template'),
    url(r'^upload_form', 'template_testing.upload_form'),
    url(r'^test_template', 'template_testing.test_template'),
    
    #Log usage data
    #url(r'^log', 'views.log'),
    
    #Functions for importing android data
    #url(r'^parseSaveLogItems', 'analysis.parseSaveLogItems'),
    #url(r'^importAndroidData', 'analysis.importAndroidData'),
    #url(r'^generateAndroidOutput', 'analysis.generateAndroidOutput'),
    #Functions for data cleaning/preprocessing
    #url(r'^correct_transcriptions', 'analysis.correct_transcriptions'),
    #url(r'^fillUserFormCondition', 'analysis.fillUserFormCondition'),
    #Full pipeline will import and clean all android data
    #url(r'^full_pipeline', 'analysis.full_pipeline'),
    
    #Data views from transcription study.
    #url(r'^analyseTarget/(?P<userName>\w*)/(?P<formName>\w*)', 'analysis.analyse_target'),
    #analyse will return reports on everyone can take a few optional parameters
    #startswith - filter only the usernames that start with the given string
    #format - sets the output format to csv, html or json (default is html)
    #url(r'^analyse', 'analysis.analyse'),
    
    #XLSForm scannable paper form generator
    url(r'^xlsform/$', 'xlsform.views.index'),
    #This is a redirect to avoid breaking the links I've given to VR.
    (r'^xlsform/scan$', redirect_to, {'url': '/xlsform/'}),
    
    (r'^xlsform/download/(?P<path>.*)$', 'xlsform.views.download'),
    (r'^xlsform/serve_json/(?P<path>.*)$', 'xlsform.views.serve_json'),
    
    url(r'^uploadForms', 'views.handle_upload'),
    (r'^uploader/', 'views.uploader'),
)
