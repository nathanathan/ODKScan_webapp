from django.http import HttpResponse
from django.shortcuts import render_to_response
from django import forms
from django.core.context_processors import csrf

import datetime
import tempfile
import os


SERVER_TMP_DIR = '/tmp'

class UploadFileForm(forms.Form):
    username = forms.HiddenInput()
    testImage  = forms.FileField()

def index(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            error = None
            warnings = None
            
            filename, ext = os.path.splitext(request.FILES['testImage'].name)
            
            #Make a randomly generated directory to prevent name collisions
            temp_dir = tempfile.mkdtemp(dir=SERVER_TMP_DIR)
            out_path = os.path.join(temp_dir, filename + '.json')
            #Init the output xml file.
            fo = open(out_path, "wb+")
            fo.close()
            
            try:
                raise Exception('x')
                
            except Exception as e:
                error = 'Error: ' + str(e)
            
            return render_to_response('upload.html', {
                'form': UploadFileForm(),#Create a new empty form
                'dir': os.path.split(temp_dir)[-1],
                'name' : filename + '.json',
                'error': error,
                'warnings': warnings,
            })
        else:
            #Fall through and use the invalid form
            pass
    else:
        form = UploadFileForm() #Create a new empty form
        
    return render_to_response('upload.html', {
        'form': form,
    })