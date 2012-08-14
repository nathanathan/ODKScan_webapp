from django.contrib.auth.models import User
from ODKScan_webapp.models import Template, FormImage, LogItem
from django.http import HttpResponse, HttpResponseBadRequest
import sys, os, tempfile
import json, codecs
from django.shortcuts import render_to_response, redirect
from django.core.context_processors import csrf
from django.template import RequestContext, loader
import ODKScan_webapp.utils as utils

def group_by_prefix(dict):
    """
    Creates a new dictionary that groups the entries in the given dictionary by the prefix of its keys before the first '-'
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
            json_path = os.path.join(form_image.output_path, 'users', str(request.user), 'output.json')#TODO
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
    
def form_view(request):
    t = loader.get_template('formView.html')
    c = RequestContext(request, {})
    return HttpResponse(t.render(c))

def field_view(request):
    t = loader.get_template('fieldView.html')
    c = RequestContext(request, {})
    return HttpResponse(t.render(c))

def log(request):
    c = {}
    c.update(csrf(request))
    if request.method == 'POST': # If the form has been submitted...
        li_params = query_dict_to_dict(request.POST)
        
        #print >>sys.stderr, li_params
        li_params['user'] = request.user
        if 'formImage' in li_params:
            li_params['formImage'] = FormImage.objects.get(id=li_params['formImage'])
        log_item = LogItem(**li_params)
        log_item.save()
        return HttpResponse("hi")
    else:
        return HttpResponseBadRequest("Only post requests please.")

from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
SERVER_TMP_DIR = os.path.join(settings.MEDIA_ROOT, 'tmp')
import socket

#TODO: Delete temp directories.
#TODO: Make user accounts to keep files separate.
@csrf_exempt
def upload_template(request):
    """
    Upload a template json and image file to the server
    """
    HOSTNAME = socket.gethostbyname(request.META['SERVER_NAME'])
    if request.method == 'POST':
        username = request.POST.get("username", "test")
        userdir = os.path.join(SERVER_TMP_DIR, username)
        try:
            os.makedirs(userdir)
        except:
            pass
        filename, ext = os.path.splitext(request.FILES['templateImage'].name)
        imagepath = os.path.join(userdir, 'form.jpg') #could be trouble if the image isn't a jpg
        
        fo = open(imagepath, "wb+")
        fo.write(request.FILES['templateImage'].read())
        fo.close()
        
        jsonpath = os.path.join(userdir, 'template.json')
        fo = open(jsonpath, "wb+")
        fo.write(request.POST['templateJson'])
        fo.close()
        return HttpResponse(json.dumps({
                                        "username":username,
                                        "imageUploadURL":'http://'+HOSTNAME+'/upload_form?username='+username,
                                        }))

from django.http import HttpResponseRedirect
#TODO: Could use a token here
@csrf_exempt
def test_template(request):
    """
    Upload a image and process it with the given template.
    """
    HOSTNAME = socket.gethostbyname(request.META['SERVER_NAME'])
    if request.method == 'POST':
        username = request.POST.get("username", "test")
        userdir = os.path.join(SERVER_TMP_DIR, username)
        filename, ext = os.path.splitext(request.FILES['testImage'].name)
        imagepath = os.path.join(userdir, 'testImage' + ext) #could be trouble if the image isn't a jpg
        fo = open(imagepath, "wb+")
        fo.write(request.FILES['testImage'].read())
        fo.close()
        #This is where we make the call to ODKScan core
        output_path = os.path.join(userdir, 'output')
        try:
            os.makedirs(output_path)
        except:
            pass
        import subprocess
        #TODO: Move APP_ROOT?
        APP_ROOT = os.path.dirname(__file__)
        #TODO: Consider adding support for a run configuration JSON file that can be passed in instead of a bunch of parameters.
        stdoutdata, stderrdata = subprocess.Popen(['./ODKScan.run',
                          userdir + '/',
                          imagepath,
                          output_path
                          ],
            cwd=os.path.join(APP_ROOT,
                             'ODKScan-core'),
            env={'LD_LIBRARY_PATH':'/usr/local/lib'}, #TODO: This could cause problems on other systems, document or fix
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE).communicate()
        print >>sys.stdout, stdoutdata
        markedup_path = os.path.join(output_path, 'markedup.jpg')
        if not os.path.exists(markedup_path):
            return HttpResponse("No marked-up image")
        
        return HttpResponse(HOSTNAME + '/formView?formLocation=/media/tmp/'+username+'/output/') #+ urlencode(params))
#        fo = open(markedup_path)
#        response = HttpResponse(mimetype='image/jpg')
#        #response['Content-Disposition'] = 'attachment; filename=output.jpg'
#        response.write(fo.read())
#        fo.close()
#        return response

