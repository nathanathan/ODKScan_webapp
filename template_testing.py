from django.contrib.auth.models import User
from ODKScan_webapp.models import Template, FormImage, LogItem
from django.http import HttpResponse, HttpResponseBadRequest
import sys, os, tempfile, shutil
import json, codecs
from django.shortcuts import render_to_response, redirect
from django.core.context_processors import csrf
from django.template import RequestContext, loader
import ODKScan_webapp.utils as utils
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
        sessionToken = request.POST.get("sessionToken", "test")
        sessionDir = os.path.join(SERVER_TMP_DIR, sessionToken)
        try:
            os.makedirs(sessionDir)
        except:
            pass
        filename, ext = os.path.splitext(request.FILES['image'].name)
        imagepath = os.path.join(sessionDir, 'form.jpg') #could be trouble if the image isn't a jpg
        
        fo = open(imagepath, "wb+")
        fo.write(request.FILES['image'].read())
        fo.close()
        
        jsonpath = os.path.join(sessionDir, 'template.json')
        fo = open(jsonpath, "wb+")
        fo.write(request.POST['templateJson'])
        fo.close()
        return HttpResponse(json.dumps({
                                        "sessionToken":sessionToken,
                                        }))
@csrf_exempt
def upload_form(request):
    """
    Upload a template json and image file to the server
    """
    HOSTNAME = socket.gethostbyname(request.META['SERVER_NAME'])
    if request.method == 'POST':
        sessionToken = request.POST.get("sessionToken", "test")
        sessionDir = os.path.join(SERVER_TMP_DIR, sessionToken)
        try:
            os.makedirs(sessionDir)
        except:
            pass
        filename, ext = os.path.splitext(request.FILES['image'].name)
        imagepath = os.path.join(sessionDir, 'testImage.jpg') #could be trouble if the image isn't a jpg
        
        fo = open(imagepath, "wb+")
        fo.write(request.FILES['image'].read())
        fo.close()
        
#        #Remove the output directory so the form will be reprocessed.
#        output_path = os.path.join(sessionDir, 'output')
#        try:
#            shutil.rmtree(output_path)
#        except:
#            pass
        
        return HttpResponse(json.dumps({
                                        "sessionToken":sessionToken,
                                        }))
        
from django.http import HttpResponseRedirect
#TODO: Could use a token here
@csrf_exempt
def test_template(request):
    """
    Upload a image and process it with the given template.
    """
    if request.method == 'POST':
        sessionToken = request.POST.get("sessionToken", "test")
        sessionDir = os.path.join(SERVER_TMP_DIR, sessionToken)
        imagepath = os.path.join(sessionDir, 'testImage.jpg') #could be trouble if the image isn't a jpg
        if not os.path.exists(os.path.join(sessionDir, 'form.jpg')):
            return HttpResponse("No template image")
        if not os.path.exists(imagepath):
            return HttpResponse("No test image.")
        
        output_path = os.path.join(sessionDir, 'output')
        try:
            os.makedirs(output_path)
        except:
            pass
        import subprocess
        #TODO: Move APP_ROOT?
        APP_ROOT = os.path.dirname(__file__)
        #TODO: Consider adding support for a run configuration JSON file that can be passed in instead of a bunch of parameters.
        
        #TODO: Make ODKScan core overwirte the features if the image/template file is newer.
        try:
            os.remove(os.path.join(sessionDir, "cached_features.yml"))
        except:
            pass
        
        stdoutdata, stderrdata = subprocess.Popen(['./ODKScan.run',
                          sessionDir + '/',
                          imagepath,
                          output_path
                          ],
            cwd=os.path.join(APP_ROOT,
                             'ODKScan-core'),
            env={'LD_LIBRARY_PATH':'/usr/local/lib'}, #TODO: This could cause problems on other systems, document or fix
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE).communicate()
        print >>sys.stdout, stdoutdata
        if not os.path.exists(os.path.join(output_path, 'aligned.jpg')):
            return HttpResponse("Could not align")
        if not os.path.exists(os.path.join(output_path, 'markedup.jpg')):
            return HttpResponse("Could not process")
        return HttpResponseRedirect('/formView?formLocation=/media/tmp/'+sessionToken+'/output/') #+ urlencode(params))
