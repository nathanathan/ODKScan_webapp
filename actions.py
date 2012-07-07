from django.template import RequestContext, loader
from django.http import HttpResponse
from django.http import HttpResponseRedirect
import json, codecs
import sys, os, tempfile

##Deprecated
#def process_json_output(pyobj):
#    """
#    Modifies segment image paths and sizes so it is easy to use them in the transcribe.html template.
#    """
#    for field in pyobj['fields']:
#        for segment in field['segments']:
#            #Modify path
#            image_path = segment.get('image_path')
#            if not image_path: continue
#            segment['name'] = os.path.basename(image_path.split("media")[1]).split(".jpg")[0]
#            #Modify image size
#            dpi = 100.0 #A guess for dots per inch
#            segment_width = segment.get("segment_width", field.get("segment_width", pyobj.get("segment_width")))
#            segment_height = segment.get("segment_height", field.get("segment_height", pyobj.get("segment_height")))
#            if not segment_width or not segment_height: continue
#            #segment['width_inches'] = float(segment_width) / dpi
#            #segment['height_inches'] = float(segment_height) / dpi
#    return pyobj

def process_json_output(filepath):
    """
    Modifies segment image paths and sizes so it is easy to use them in the transcribe.html template.
    """
    import json, codecs
    fp = codecs.open(filepath, mode="r", encoding="utf-8")
    pyobj = json.load(fp, encoding='utf-8')#This is where we load the json output
    for field in pyobj['fields']:
        if field['type'] is 'select':
            #This is because xforms use space to delimit options while the jquery val function uses commas
            field['value'] = field['value'].replace(' ', ',')
        for segment in field['segments']:
            #Modify path
            image_path = segment.get('image_path')
            if not image_path: continue
            segment['name'] = os.path.basename(image_path.split("media")[1]).split(".jpg")[0]
            #Modify image size
            #dpi = 100.0 #A guess for dots per inch
            #segment_width = segment.get("segment_width", field.get("segment_width", pyobj.get("segment_width")))
            #segment_height = segment.get("segment_height", field.get("segment_height", pyobj.get("segment_height")))
            #if not segment_width or not segment_height: continue
            #segment['width_inches'] = float(segment_width) / dpi
            #segment['height_inches'] = float(segment_height) / dpi
    return pyobj

def process_forms(modeladmin, request, queryset):
        #This is where we make the call to ODKScan core
        import subprocess
        #TODO: Move APP_ROOT?
        APP_ROOT = os.path.dirname(__file__)
        
        for obj in queryset:
            if not obj.status or obj.status == 'e':
                #print >>sys.stderr, obj.output_path
                #This blocks, for scaling we should add a "processing" status and do it asyncronously.
                stdoutdata, stderrdata = subprocess.Popen(['./ODKScan.run',
                                  os.path.dirname(obj.template.image.path) + '/',
                                  obj.image.path,
                                  obj.output_path
                                  ],
                    cwd=os.path.join(APP_ROOT,
                                     'ODKScan-core'),
                    env={'LD_LIBRARY_PATH':'/usr/local/lib'}, #TODO: This could cause problems on other systems, document or fix
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE).communicate()
                print >>sys.stdout, stdoutdata
                obj.error_message = stderrdata
                json_path = os.path.join(obj.output_path, 'output.json')
                if os.path.exists(json_path):
                    process_json_output(json_path)#Not sure I need this.
                    obj.status = 'p'
                else:
                    obj.status = 'e'
                obj.save()
process_forms.short_description = "Process selected forms."

def renderTableView(modeladmin, request, queryset, autofill, showSegs):
    form_template = None
    json_outputs = []
    for formImage in queryset:
        if formImage.status == 'f':
            raise Exception("You cannot transcribe a finalized from.")
        if form_template is None:
            form_template = formImage.template
        elif form_template.name != formImage.template.name:
            raise Exception("Mixed templates: " + form_template.name + " and " + formImage.template.name)
        
        json_path = os.path.join(formImage.output_path, 'output.json')
        if not os.path.exists(json_path):
            continue
        user_json_path = os.path.join(formImage.output_path, 'users', str(request.user), 'output.json')
        if not os.path.exists(user_json_path):
            try:
                os.makedirs(os.path.dirname(user_json_path))
            except:
                pass
            fp = codecs.open(json_path, mode="r", encoding="utf-8")
            pyobj = json.load(fp, encoding='utf-8')#This is where we load the json output
            fp.close()
            pyobj['form_id'] = int(formImage.id)
            pyobj['outputDir'] = os.path.basename(formImage.output_path)
            pyobj['imageName'] = str(formImage)
            pyobj['templateName'] = form_template.name
            pyobj['userName'] = str(request.user)
            pyobj['autofill'] = autofill
            pyobj['showSegs'] = showSegs
            from ODKScan_webapp.views import print_pyobj_to_json
            print_pyobj_to_json(pyobj, user_json_path)
        json_path = user_json_path

        fp = codecs.open(json_path, mode="r", encoding="utf-8")
        pyobj = json.load(fp, encoding='utf-8')#This is where we load the json output
        fp.close()
        json_outputs.append(pyobj)
        #print >>sys.stderr, json.dumps(pyobj, ensure_ascii=False, indent=4)
    if form_template is None:
        raise Exception("no template")
    form_template_fp = codecs.open(form_template.json.path, mode="r", encoding="utf-8")
    json_template = json.load(form_template_fp, encoding='utf-8')
    t = loader.get_template('transcribe.html')
    c = RequestContext(request, {
                 'template_name':form_template.name,
                 'json_template':json_template,
                 'json_outputs':json_outputs,
                 'user':request.user,
                 'autofill':autofill,
                 'showSegs':showSegs,
                 })
    return t.render(c)

def transcribe(modeladmin, request, queryset):
    return HttpResponse(renderTableView(modeladmin, request, queryset, True, True))
transcribe.short_description = "Transcribe selected forms."

def transcribeNoImages(modeladmin, request, queryset):
    return HttpResponse(renderTableView(modeladmin, request, queryset, True, False))
transcribeNoImages.short_description = "Transcribe (no images)"

def transcribeNoAutofill(modeladmin, request, queryset):
    return HttpResponse(renderTableView(modeladmin, request, queryset, False, True))
transcribeNoAutofill.short_description = "Transcribe (no autofill)"

def transcribeNoEverything(modeladmin, request, queryset):
    return HttpResponse(renderTableView(modeladmin, request, queryset, False, False))
transcribeNoEverything.short_description = "Transcribe (no images, no autofill)"

#TODO: Pass it getparams
#def transcribeFormView(modeladmin, request, queryset):
#    form_template = None
#    json_outputs = []
#    formImage = queryset[0]
#    params = {
#              'formId': formImage.id,
#              'formLocation': '/media/' + os.path.basename(formImage.output_path) + '/',
#              'user':request.user,
#              }
#    from urllib import urlencode
#    return HttpResponseRedirect('/formView/?' + urlencode(params))


#def transcribeFormView(modeladmin, request, queryset):
#    for formImage in queryset:
#        pass
#    t = loader.get_template('formViewSet.html')
#    c = RequestContext(request, {
#                 'formset':queryset,
#                 'formLocation': '/media/' + os.path.basename(formImage.output_path) + '/',
#                 'user':request.user,
#                 })
#    return HttpResponse(t.render(c))


def transcribeFormView(modeladmin, request, queryset):
    form_template = None
    json_outputs = []
    for formImage in queryset:
        if formImage.status == 'f':
            raise Exception("You cannot transcribe a finalized from.")
        if form_template is None:
            form_template = formImage.template
        elif form_template.name != formImage.template.name:
            raise Exception("Mixed templates: " + form_template.name + " and " + formImage.template.name)
        
        json_path = os.path.join(formImage.output_path, 'output.json')
        if not os.path.exists(json_path):
            continue
        user_json_path = os.path.join(formImage.output_path, 'users', str(request.user), 'output.json')
        if not os.path.exists(user_json_path):
            try:
                os.makedirs(os.path.dirname(user_json_path))
            except:
                pass
            fp = codecs.open(json_path, mode="r", encoding="utf-8")
            pyobj = json.load(fp, encoding='utf-8')#This is where we load the json output
            fp.close()
            pyobj['form_id'] = int(formImage.id)
            pyobj['outputDir'] = os.path.basename(formImage.output_path)
            pyobj['imageName'] = str(formImage)
            pyobj['templateName'] = form_template.name
            pyobj['userName'] = str(request.user)
            pyobj['formView'] = True
            from ODKScan_webapp.views import print_pyobj_to_json
            print_pyobj_to_json(pyobj, user_json_path)
        json_path = user_json_path

        fp = codecs.open(json_path, mode="r", encoding="utf-8")
        pyobj = json.load(fp, encoding='utf-8')#This is where we load the json output
        fp.close()
        json_outputs.append(pyobj)
        #print >>sys.stderr, json.dumps(pyobj, ensure_ascii=False, indent=4)
    if form_template is None:
        raise Exception("no template")
    form_template_fp = codecs.open(form_template.json.path, mode="r", encoding="utf-8")
    json_template = json.load(form_template_fp, encoding='utf-8')
    t = loader.get_template('formViewSet.html')
    c = RequestContext(request, {
                 'template_name':form_template.name,
                 'json_template':json_template,
                 'json_outputs':json_outputs,
                 'user':request.user,
                 })
    return HttpResponse(t.render(c))
transcribeFormView.short_description = "Transcribe (formView)"

def finalize(modeladmin, request, queryset):
    """
    Finalize prevents further editing on form image transcriptions.
    """
    queryset.update(status='f')
finalize.short_description = "Finalize selected forms."

def json_output_to_field_dict(json_output):
    field_dict = {}
    for field in json_output.get('fields'):
        field_value = field.get('transcription', field.get('value'))
        if field_value:
            field_dict[field['name']] = field_value
    return field_dict

def dict_to_csv(dict_array, csvfile):
    """
    Convert an array of dictionaries to a csv where the keys are the column headers.
    """
    import csv
    column_headers = set()
    for row in dict_array:
        column_headers = column_headers.union(row.keys())
    csv_writer = csv.DictWriter(csvfile, column_headers, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
    header_dict = dict((x,x) for x in column_headers)
    csv_writer.writerow(header_dict)
    csv_writer.writerows(dict_array)

def generate_csv(modeladmin, request, queryset):
    dict_array = []
    form_template = None
    for formImage in queryset:
        json_path = os.path.join(formImage.output_path, 'output.json')
        if not os.path.exists(json_path):
            raise Exception('No json for form image')
        if form_template is None:
            form_template = formImage.template
        elif form_template.name != formImage.template.name:
            raise Exception("Mixed templates: " + form_template.name + " and " + formImage.template.name)
        fp = codecs.open(json_path, mode="r", encoding="utf-8")
        pyobj = json.load(fp, encoding='utf-8')#This is where we load the json output
        fp.close()
        dict_array.append(json_output_to_field_dict(pyobj))
    temp_file = tempfile.mktemp()
    csvfile = open(temp_file, 'wb')
    dict_to_csv(dict_array, csvfile)
    csvfile.close()
    response = HttpResponse(mimetype='application/octet-stream')
    response['Content-Disposition'] = 'attachment; filename=output.csv'
    fo = open(temp_file)
    response.write(fo.read())
    fo.close()
    return response
generate_csv.short_description = "Generate CSV from selected forms."


#def save_transcriptions(request):
#    c = {}
#    c.update(csrf(request))
#    if request.method == 'POST': # If the form has been submitted...
#        row_dict = group_by_prefix(request.POST)
#        for formImageId, transcription in row_dict.items():
#            form_image = FormImage.objects.get(id=formImageId)
#            json_path = os.path.join(form_image.output_path, 'output.json')
#            if not os.path.exists(json_path):
#                raise Exception('No json for form image')
#            fp = codecs.open(json_path, mode="r", encoding="utf-8")
#            pyobj = json.load(fp, encoding='utf-8')#This is where we load the json output
#            fp.close()
#            for field in pyobj.get('fields'):
#                field_transcription = transcription.get(field['name'])
#                if field_transcription:
#                    field['transcription'] = field_transcription
#            print_pyobj_to_json(pyobj, json_path)
#            form_image.status = 'm'
#            form_image.save()
#            return HttpResponse("hello")
#    else:
#        return HttpResponseBadRequest("Only post requests please.")