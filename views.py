from django.contrib.auth.models import User
from ODKScan_webapp.models import Template, FormImage, LogItem
from django.http import HttpResponse, HttpResponseBadRequest
import sys, os, tempfile, shutil
import json, codecs
from django.shortcuts import render_to_response, redirect
from django.core.context_processors import csrf
from django.template import RequestContext, loader
import ODKScan_webapp.utils as utils

# def index(request):
#     template = loader.get_template('index.html')
#     context = Context({})
#     return HttpResponse(template.render(context))

def group_by_prefix(dict):
    """
    Creates a new dictionary that groups the entries in the given dictionary by
    the prefix of its keys before the first '-'
    Ex:
    {"1-a":1, "2-a":1, "2-b":2} -> {"1":{"a":1}, "2":{"a":1, "b":2}}
    Items without a prefix are thown out.
    """
    new_dict = {}
    for key, value in dict.items():
        prefix, dash, suffix = key.partition('-')
        if prefix and suffix:
            group = new_dict.get(prefix, {})
            group[suffix] = value
            new_dict[prefix] = group
    return new_dict

def query_dict_to_dict(q_dict, joiner=','):
    """
    Transform a query dict into a standard dict by joining it's values
    """
    dict = {}
    for key, value_list in q_dict.lists():
        dict[key] = joiner.join(value_list)
    return dict

def save_transcriptions(request):
    c = {}
    c.update(csrf(request))
    if request.method == 'POST': # If the form has been submitted...
        #Logging:
        LogItem.objects.create(user=request.user,
                       activity='save_transcriptions',
                       forms=','.join(request.POST.keys())
                       ).save()
        row_dict = group_by_prefix(query_dict_to_dict(request.POST))
        for formImageId, transcription in row_dict.items():
            form_image = FormImage.objects.get(id=formImageId)
            json_path = os.path.join(form_image.output_path, 'transcription.json')
            if not os.path.exists(json_path):
                raise Exception('No json for form image')
            fp = codecs.open(json_path, mode="r", encoding="utf-8")
            pyobj = json.load(fp, encoding='utf-8')#This is where we load the json output
            fp.close()
            for field in pyobj.get('fields'):
                field_transcription = transcription.get(field['name'])
                if field_transcription:
                    field['transcription'] = field_transcription
            utils.print_pyobj_to_json(pyobj, json_path)
            form_image.status = 'm'
            form_image.save()
        return HttpResponse()
    else:
        return HttpResponseBadRequest("Only post requests please.")
    
# def form_view(request):
#     t = loader.get_template('formView.html')
#     c = RequestContext(request, {})
#     return HttpResponse(t.render(c))
# 
# def field_view(request):
#     t = loader.get_template('fieldView.html')
#     c = RequestContext(request, {})
#     return HttpResponse(t.render(c))

# def log(request):
#     c = {}
#     c.update(csrf(request))
#     if request.method == 'POST': # If the form has been submitted...
#         li_params = query_dict_to_dict(request.POST)
#         
#         #print >>sys.stderr, li_params
#         li_params['user'] = request.user
#         if 'formImage' in li_params:
#             li_params['formImage'] = FormImage.objects.get(id=li_params['formImage'])
#         log_item = LogItem(**li_params)
#         log_item.save()
#         return HttpResponse("hi")
#     else:
#         return HttpResponseBadRequest("Only post requests please.")
