from django.http import HttpResponse
from django.http import HttpResponseRedirect
import sys
from django.shortcuts import render_to_response


def save_transcription(request):
    if request.method == 'GET': # If the form has been submitted...
        print >>sys.stderr, "get"
    return HttpResponseRedirect("http://google.com")
#        form = UploadFileForm(request.POST, request.FILES) # A form bound to the POST data
#        if form.is_valid(): # All validation rules pass
#            
#            error = None
#            warnings = None
#            
#            filename, ext = os.path.splitext(request.FILES['file'].name)
#            
#            #Make a randomly generated directory to prevent name collisions
#            temp_dir = tempfile.mkdtemp(dir=SERVER_TMP_DIR)
#            xml_path = os.path.join(temp_dir, filename + '.xml')
#            
#            #Init the output xml file.
#            fo = open(xml_path, "wb+")
#            fo.close()
#            
#            try:
#                #TODO: use the file object directly
#                xls_path = handle_uploaded_file(request.FILES['file'], temp_dir)
#                warnings = []
#                json_survey = xls2json.parse_file_to_json(xls_path, warnings=warnings)
#                survey = pyxform.create_survey_element_from_dict(json_survey)
#                survey.print_xform_to_file(xml_path)
#                
#            except Exception as e:
#                error = 'Error: ' + str(e)
#            
#            return render_to_response('result.html', {
#                'xml_path' : '.' + xml_path,
#                'error': error,
#                'warnings': warnings
#            })
#    else:
#        form = UploadFileForm() # An unbound form
#        
#    return render_to_response('upload.html', {
#        'form': form,
#    })