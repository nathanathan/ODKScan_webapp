from django.template import RequestContext, loader
from django.http import HttpResponse
from django.http import HttpResponseRedirect
import json, codecs
import sys, os, tempfile

def process_json_output(pyobj):
    """
    Modifies segment image paths and sizes so it is easy to use them in the transcribe.html template.
    """
    for field in pyobj['fields']:
        for segment in field['segments']:
            #Modify path
            image_path = segment.get('image_path')
            if not image_path: continue
            segment['image_path'] = "/media" + image_path.split("media")[1]
            #Modify image size
            dpi = 100.0 #A guess for dots per inch
            segment_width = segment.get("segment_width", field.get("segment_width", pyobj.get("segment_width")))
            segment_height = segment.get("segment_height", field.get("segment_height", pyobj.get("segment_height")))
            if not segment_width or not segment_height: continue
            #segment['width_inches'] = float(segment_width) / dpi
            #segment['height_inches'] = float(segment_height) / dpi
    return pyobj

def transcribe(modeladmin, request, queryset):
    form_template = None
    json_outputs = []
    for formImage in queryset:
        json_path = os.path.join(formImage.output_path, 'output.json')
        if formImage.status == 'f':
            raise Exception("You cannot transcribe a finalized from.")
        if not os.path.exists(json_path):
            continue
        if form_template is None:
            form_template = formImage.template
        elif form_template.name != formImage.template.name:
            raise Exception("Mixed templates: " + form_template.name + " and " + formImage.template.name)
        fp = codecs.open(json_path, mode="r", encoding="utf-8")
        pyobj = json.load(fp, encoding='utf-8')#This is where we load the json output
        pyobj['formImage'] = formImage
        process_json_output(pyobj)
        json_outputs.append(pyobj)
        #print >>sys.stderr, json.dumps(pyobj, ensure_ascii=False, indent=4)
    if form_template is None:
        raise Exception("no template")
    form_template_fp = codecs.open(form_template.json.path, mode="r", encoding="utf-8")
    json_template = json.load(form_template_fp, encoding='utf-8')
    t = loader.get_template('transcribe.html')
    c = RequestContext(request, {
                 'json_template_name':form_template.name,
                 'json_template':json_template,
                 'json_outputs':json_outputs,
                 })
    return HttpResponse(t.render(c))
transcribe.short_description = "Transcribe selected forms."

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

def save_transcriptions(request):
    c = {}
    c.update(csrf(request))
    if request.method == 'POST': # If the form has been submitted...
        row_dict = group_by_prefix(request.POST)
        for formImageId, transcription in row_dict.items():
            form_image = FormImage.objects.get(id=formImageId)
            json_path = os.path.join(form_image.output_path, 'output.json')
            if not os.path.exists(json_path):
                raise Exception('No json for form image')
            fp = codecs.open(json_path, mode="r", encoding="utf-8")
            pyobj = json.load(fp, encoding='utf-8')#This is where we load the json output
            fp.close()
            for field in pyobj.get('fields'):
                field_transcription = transcription.get(field['name'])
                if field_transcription:
                    field['transcription'] = field_transcription
            print_pyobj_to_json(pyobj, json_path)
            form_image.status = 'm'
            form_image.save()
            return HttpResponse("hello")
    else:
        return HttpResponseBadRequest("Only post requests please.")