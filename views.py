from django.contrib.auth.models import User
from ODKScan_webapp.models import Template, FormImage, LogItem, UserFromCondition
from django.http import HttpResponse, HttpResponseBadRequest
import sys, os, tempfile
import json, codecs
from django.shortcuts import render_to_response, redirect
from django.core.context_processors import csrf
from django.template import RequestContext, loader
from django.db.models import Max, Min, Count, Avg

def print_pyobj_to_json(pyobj, path=None):
    """
    dump a python nested array/dict structure to the specified file or stdout if no file is specified
    """
    if path:
        fp = codecs.open(path, mode="w", encoding="utf-8")
        json.dump(pyobj, fp=fp, ensure_ascii=False)#, indent=4)
        fp.close()
    else:
        print json.dumps(pyobj, ensure_ascii=False, indent=4)

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
            print_pyobj_to_json(pyobj, json_path)
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
    
def levenshtein(s1, s2):
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if not s1:
        return len(s2)
 
    previous_row = xrange(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1 # j+1 instead of j since previous_row and current_row are one character longer
            deletions = current_row[j] + 1       # than s2
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
 
    return previous_row[-1]

#def get_total_edits(queryset):
#    for log_item in queryset:

def gen_form_stats(pyobj):
    stats = {}
    stats['number_of_fields'] = len(pyobj['fields'])
    for field in pyobj['fields']:
        if 'transcription' in field:
            stats['fields_transcribed'] = stats.get('fields_transcribed', 0) + 1
            if 'value' in field:
                if field['value'] == field['transcription']:
                    stats['fields_transcribed_unmodified'] = stats.get('fields_transcribed_unmodified', 0) + 1
                else:
                    stats['fields_transcribed_modified'] = stats.get('fields_transcribed_modified', 0) + 1
                if 'actual_value' in field:
                    if field['actual_value'] == field['transcription']:
                        stats['correct_transcribed_fields'] = stats.get('correct_transcribed_fields', 0) + 1
                    else:
                        stats['incorrect_transcribed_fields'] = stats.get('incorrect_transcribed_fields', 0) + 1
    return stats

def load_json_to_pyobj(path):
    fp = codecs.open(path, mode="r", encoding="utf-8")
    pyobj = json.load(fp, encoding='utf-8')
    fp.close()
    return pyobj

def fillUserFromCondition(request):
    """
    This is really REALLY slow, would be better to iterate though users and forms.
    """
    for logItem in LogItem.objects.all():
        if logItem.formImage:
            user_dir = os.path.join(logItem.formImage.output_path, 'users')
            json_path = os.path.join(user_dir, logItem.user.username, 'output.json')
            pyobj = load_json_to_pyobj(json_path)
            try:
                UserFromCondition.objects.create(user=logItem.user,
                                                 formImage=logItem.formImage,
                                                 tableView=(not pyobj.get('formView', False)),
                                                 formView=pyobj.get('formView', False),
                                                 showSegs=pyobj.get('showSegs', False),
                                                 autofill=pyobj.get('autofill', False)
                                                 ).save()
            except:
                pass
    return HttpResponse("done", mimetype="application/json")

def analyse_transcriptions(request):
    fi_dict = {}
    for form_image in FormImage.objects.all():
        user_dir = os.path.join(form_image.output_path, 'users')
        user_list = []
        user_dict = {}
        if os.path.exists(user_dir):
            user_list = os.listdir(user_dir)
            for user in user_list:
                userObject = User.objects.get(username=user)
                #Filter by user properties here
                json_path = os.path.join(user_dir, user, 'output.json')
                pyobj = load_json_to_pyobj(json_path)
                userStats = gen_form_stats(pyobj)
                filtered_log_items = LogItem.objects.filter(user=userObject, formImage=form_image)
                startEndStamp = filtered_log_items.aggregate(Max('timestamp'), Min('timestamp'))
                if startEndStamp.get('timestamp__max'):
                    userStats['time_spent'] = str(startEndStamp['timestamp__max'] - startEndStamp['timestamp__min'])
                #userStats['fields_logitems'] = LogItem.objects.filter(user=userObject, formImage=form_image).values('fieldName').annotate(modifications=Count('pk'), end=Max('timestamp'), start=Min('timestamp'))
                fieldNames = filtered_log_items.values('fieldName').annotate()
                backspaces = 0
                chars_added = 0
                for fieldName in fieldNames:
                    previous = None
                    for log_item in filtered_log_items.filter(fieldName=fieldName['fieldName']).order_by('timestamp').all():
                        if previous:
                            cur = log_item.newValue if log_item.newValue else ''
                            difference = len(cur) - len(previous)
                            if difference > 0:
                                chars_added += difference
                            else:
                                backspaces -= difference
                        previous = log_item.newValue
                userStats['backspaces'] = backspaces
                userStats['chars_added'] = chars_added
                user_dict[user] = userStats
        fi_dict[str(form_image)] = user_dict
    t = loader.get_template('analyseTranscriptions.html')
    c = RequestContext(request, {"formImages" : fi_dict})
    return HttpResponse(t.render(c))

def to_pyobj(djm):
    pyobj = {}
    for field in djm.all():
        fieldout = {}
        fieldout['time_spent'] = str(field['end'] - field['start'])
        fieldout['modifications'] = field['modifications']
        pyobj[field['fieldName']] = fieldout
    return pyobj

def analyse_group(request, username=None):
    fi_dict = {}
    for form_image in FormImage.objects.all():
        user_dir = os.path.join(form_image.output_path, 'users')
        user = username
        json_path = os.path.join(user_dir, user, 'output.json')
        if os.path.exists(json_path):
            pyobj = load_json_to_pyobj(json_path)
            userStats = gen_form_stats(pyobj)
            userObject = User.objects.get(username=user)
            startEndStamp = LogItem.objects.filter(user=userObject, formImage=form_image).aggregate(Max('timestamp'), Min('timestamp'))
            if startEndStamp.get('timestamp__max'):
                userStats['time_spent'] = str(startEndStamp['timestamp__max'] - startEndStamp['timestamp__min'])
            userStats['fields_logitems'] = to_pyobj(LogItem.objects.filter(user=userObject, formImage=form_image).values('fieldName').annotate(modifications=Count('pk'), end=Max('timestamp'), start=Min('timestamp')))
            fi_dict[str(form_image)] = userStats
    return HttpResponse(json.dumps(fi_dict), mimetype="application/json")

def add_to_correct_transcription(correct_transcription, transcription):
    ct_fields = correct_transcription.get('fields')
    if not ct_fields:
        ct_fields = []
        for field in transcription['fields']:
            ct_field = {}
            ct_field['name'] = field['name']
            ct_value = field.get('transcription', field.get('value'))
            ct_field['values'] = [ct_value] if ct_value else []
            ct_fields.append(ct_field)
        correct_transcription['fields'] = ct_fields
    for t_field, ct_field in zip(transcription['fields'], ct_fields):
        assert t_field['name'] == ct_field['name']
        possible_values = set(ct_field['values'])
        ct_value = t_field.get('transcription', t_field.get('value'))
        if ct_value:
            possible_values.add(str(ct_value))
        ct_field['values'] = list(possible_values)
    return correct_transcription

excluded_users = ['user', 'test1', 'test2', 'test_final']

def correct_transcriptions(request):
    fi_dict = {}
    for form_image in FormImage.objects.all():
        correct_transcription = {}
        user_dir = os.path.join(form_image.output_path, 'users')
        user_list = []
        if os.path.exists(user_dir):
            user_list = os.listdir(user_dir)
            for user in user_list:
                if user in excluded_users:
                    continue
                json_path = os.path.join(user_dir, user, 'output.json')
                pyobj = load_json_to_pyobj(json_path)
                add_to_correct_transcription(correct_transcription, pyobj)
        fi_dict[str(form_image)] = correct_transcription
        print_pyobj_to_json(correct_transcription, os.path.join(form_image.output_path, 'corrected.json'))
    return HttpResponse("done", mimetype="application/json")
    #return HttpResponse(json.dumps(fi_dict), mimetype="application/json")

