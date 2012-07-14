from django.contrib.auth.models import User
from ODKScan_webapp.models import Template, FormImage, LogItem, UserFormCondition
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
        dir, file = os.path.split(path)
        if not os.path.exists(dir):
            os.makedirs(dir)
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

android_excluded_users = ['t7']
excluded_users = ['user', 'test1', 'test2', 'test_final', 'T1', 'T2'] + android_excluded_users

def load_json_to_pyobj(path):
    fp = codecs.open(path, mode="r", encoding="utf-8")
    pyobj = json.load(fp, encoding='utf-8')
    fp.close()
    return pyobj

def gen_form_stats(pyobj, ground_truth):
    accuracy_matrix = {
                     'correct_transcription' : None,
                     'incorrect_transcription' : None,
                     'no_transcription' : None,
                     }
    for key in accuracy_matrix.keys():
        accuracy_matrix[key] = {
               'correct_autofill' : 0,
               'incorrect_autofill' : 0,
               'no_autofill' : 0,
               }
    for field, gt_field in zip(pyobj['fields'], ground_truth['fields']):
        if 'transcription' in field:
            if field['transcription'] == gt_field['value']:
                if 'value' in field and pyobj.get('autofill', True):
                    if field['value'] == gt_field['value']:
                        accuracy_matrix['correct_transcription']['correct_autofill']+=1
                    else:
                        accuracy_matrix['correct_transcription']['incorrect_autofill']+=1
                else:
                    accuracy_matrix['correct_transcription']['no_autofill']+=1
            else:
                if 'value' in field and pyobj.get('autofill', True):
                    if field['value'] == gt_field['value']:
                        accuracy_matrix['incorrect_transcription']['correct_autofill']+=1
                    else:
                        accuracy_matrix['incorrect_transcription']['incorrect_autofill']+=1
                else:
                    accuracy_matrix['incorrect_transcription']['no_autofill']+=1
        else:
            if 'value' in field and pyobj.get('autofill', True):
                if field['value'] == gt_field['value']:
                    accuracy_matrix['no_transcription']['correct_autofill']+=1
                else:
                    accuracy_matrix['no_transcription']['incorrect_autofill']+=1
            else:
                accuracy_matrix['no_transcription']['no_autofill']+=1
    
    stats = {
             'accuracy_matrix' : accuracy_matrix,
             'number_of_fields' : len(pyobj['fields']),
             }
    return stats


def analyse_transcriptions(request):
    fi_dict = {}
    for form_image in FormImage.objects.all():
        if str(form_image)[0] == 'J':
            #Filter out practice forms
            continue
        ground_truth = load_json_to_pyobj(os.path.join(form_image.output_path, 'corrected.json'))
        user_dir = os.path.join(form_image.output_path, 'users')
        user_list = []
        user_dict = {}
        if os.path.exists(user_dir):
            user_list = os.listdir(user_dir)
            for user in user_list:
                if user in excluded_users:
                    continue
                userObject = User.objects.get(username=user)
                #Filter by user properties here
                json_path = os.path.join(user_dir, user, 'output.json')
                pyobj = load_json_to_pyobj(json_path)
                userStats = gen_form_stats(pyobj, ground_truth)
                filtered_log_items = LogItem.objects.filter(user=userObject, formImage=form_image)
                condition = UserFormCondition.objects.get(user=userObject, formImage=form_image)
                if condition.tableView:
                    userStats['table_view'] = True
                    #We need to group and average times in this case since it's not necessairily sequencial
                    #formImages = FormImage.objects.filter(image__contains='/photo/'+str(form_image)[0])
                    #This query has some added uglyness because in the practice runs the forms of the same name group (i.e. J) aren't all in the same condition
                    #Perhaps I should just make an exception for them
                    formImages = UserFormCondition.objects.filter(formImage__image__contains='/photo/'+str(form_image)[0],
                                                                  user=userObject,
                                                                  tableView=True).values('formImage').annotate()
                    startEndStamp = LogItem.objects.filter(user=userObject, formImage__in=formImages).aggregate(Max('timestamp'), Min('timestamp'))
                    if startEndStamp.get('timestamp__max'):
                        userStats['time_spent'] = str((startEndStamp['timestamp__max'] - startEndStamp['timestamp__min'])/4)
                else:
                    if condition.formView:
                        userStats['form_view'] = True
                    startEndStamp = filtered_log_items.aggregate(Max('timestamp'), Min('timestamp'))
                    if startEndStamp.get('timestamp__max'):
                        userStats['time_spent'] = str(startEndStamp['timestamp__max'] - startEndStamp['timestamp__min'])
                #userStats['fields_logitems'] = LogItem.objects.filter(user=userObject, formImage=form_image).values('fieldName').annotate(modifications=Count('pk'), end=Max('timestamp'), start=Min('timestamp'))
                fieldNames = filtered_log_items.values('fieldName').annotate()
                backspaces = 0
                chars_added = 0
                total_lev_distance_traveled = 0
                for fieldName in fieldNames:
                    previous = None
                    for log_item in filtered_log_items.filter(fieldName=fieldName['fieldName']).order_by('timestamp').all():
                        if previous:
                            cur = log_item.newValue if log_item.newValue else ''
                            difference = len(cur) - len(previous)
                            total_lev_distance_traveled += abs(levenshtein(cur, previous))
                            if difference > 0:
                                chars_added += difference
                            else:
                                backspaces -= difference
                        previous = log_item.newValue
                userStats['backspaces'] = backspaces
                userStats['chars_added'] = chars_added
                userStats['total_lev_distance_traveled'] = total_lev_distance_traveled
                user_dict[str(form_image)] = userStats
                fi_dict[user] = fi_dict.get(user, {})
                fi_dict[user].update(user_dict)
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

def most_common_item(li):
    hist = {}
    for item in li:
        hist[item] = hist.get(item, 0) + 1
    max_item = None
    max_occurences = 0
    for key, value in hist.items():
        if value > max_occurences:
            max_occurences = value
            max_item = key
    return max_item

def add_to_correct_transcription(correct_transcription, transcription):
    ct_fields = correct_transcription.get('fields')
    if not ct_fields:
        ct_fields = []
        for field in transcription['fields']:
            ct_field = {}
            ct_field['name'] = field['name']
            ct_value = field.get('transcription', field.get('value'))
            ct_field['values'] = [str(ct_value)] if ct_value else []
            ct_fields.append(ct_field)
        correct_transcription['fields'] = ct_fields
    for t_field, ct_field in zip(transcription['fields'], ct_fields):
        assert t_field['name'] == ct_field['name']
        new_value = t_field.get('transcription', t_field.get('value'))
        if new_value:
            ct_field['values'].append(str(new_value))
        ct_field['unique_values'] = list(set(ct_field['values']))
        ct_field['value'] = most_common_item(ct_field['values'])
        ct_field['needs_attention'] =  len(ct_field['unique_values']) > 2 or len(ct_field['unique_values']) == 0
    return correct_transcription


def correct_transcriptions(request):
    fi_dict = {}
    for form_image in FormImage.objects.all():
        correct_transcription = {}
        
        add_to_correct_transcription(correct_transcription, load_json_to_pyobj(os.path.join(form_image.output_path, 'output.json')))
        
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
    return HttpResponse("corrected", mimetype="application/json")
    #return HttpResponse(json.dumps(fi_dict), mimetype="application/json")

def fillUserFormCondition(request):
    fi_dict = {}
    for form_image in FormImage.objects.all():
        user_dir = os.path.join(form_image.output_path, 'users')
        user_list = []
        user_dict = {}
        if os.path.exists(user_dir):
            user_list = os.listdir(user_dir)
            for user in user_list:
                if user in excluded_users:
                    continue
                userObject = User.objects.get(username=user)
                #Filter by user properties here
                json_path = os.path.join(user_dir, user, 'output.json')
                pyobj = load_json_to_pyobj(json_path)
                try:
                    UserFormCondition.objects.create(user=userObject,
                                                     formImage=form_image,
                                                     tableView=(not pyobj.get('formView', False) and not pyobj.get('android', False)),
                                                     formView=pyobj.get('formView', False),
                                                     showSegs=pyobj.get('showSegs', False),
                                                     autofill=pyobj.get('autofill', False)
                                                     ).save()
                except:
                    pass
    return HttpResponse("done", mimetype="application/json")

#Also need to genrate output.json
def importAndroidData(request):
    output = ''
    #Create the log items
    import sqlite3, time, os, re
    conn = sqlite3.connect('/home/nathan/Desktop/log.sqlite')
    c = conn.cursor()
    file_path_regex = re.compile(r"/sdcard/odk/instances/.*/report_card_(?P<form>\w\d+)_(?P<user>\w\d+)(?P<showSegs>_showSegs)?(?P<autofill>_autofill)?.xml$")
    for id,timestamp,action_type,instance_path,question_path,param1,param2 in c.execute('SELECT * FROM log'):
        if not instance_path:
            continue
        fp_parse = file_path_regex.search(instance_path)
        if fp_parse:
            fp_parse_dict = fp_parse.groupdict()
            if action_type == 'text changed':
                showSegs = fp_parse_dict['showSegs'] if fp_parse_dict['showSegs'] else ""
                autofill = fp_parse_dict['autofill'] if fp_parse_dict['autofill'] else ""
                user = fp_parse_dict['user']
                form = fp_parse_dict['form']
                if user in excluded_users:
                    continue
                li_params = {
                            'user' : User.objects.get(username=user),
                            'url' : instance_path,
                            'formImage' : FormImage.objects.get(image__contains='/photo/'+form),
                            'view' : 'android-condition' + showSegs + autofill,
                            'fieldName' : os.path.split(question_path)[-1][:-3] if question_path else None,
                            'previousValue' : param1,
                            'newValue' : param2,
                            'activity' : 'android-' + action_type,
                            'timestamp' : time.localtime(int(timestamp)*1./1000),
                          }
                #print question_path
                LogItem.objects.create(**li_params).save()
        else:
            raise Exception("Could not parse: " + str(instance_path))
    return HttpResponse(output, mimetype="application/json")
        
def generateAndroidOutput(request):
    output = ''
    import os, re
    #Create the output files from the log items
    view_regex = re.compile(r"^android-condition(?P<showSegs>_showSegs)?(?P<autofill>_autofill)?$")
    for form_image in FormImage.objects.all():
        if str(form_image)[0] == 'J':
            #Filter out practice forms
            continue
        for user in User.objects.all():
            if user in excluded_users:
                continue
            filtered_li = LogItem.objects.filter(formImage=form_image, user=user,activity='android-text changed')
            if len(filtered_li) > 0:
                path_to_initial_json = os.path.join(form_image.output_path, 'output.json')
                initial_json = load_json_to_pyobj(path_to_initial_json)
                viewParse = view_regex.search(filtered_li[0].view).groupdict()
                initial_json['autofill'] = bool(viewParse.get('autofill'))
                initial_json['showSegs'] = bool(viewParse.get('showSegs'))
                initial_json['formView'] = False
                initial_json['tableView'] = False
                initial_json['android'] = True
                for field in initial_json['fields']:
                    ordered_field_li = filtered_li.filter(fieldName=field['name']).order_by('-timestamp')
                    if len(ordered_field_li) > 0:
                        field['transcription'] = ordered_field_li[0].newValue
                    else:
                        pass
                user_json_path = os.path.join(form_image.output_path, 'users', user.username, 'output.json')
                if os.path.exists(user_json_path):
                    raise Exception('path exists: ' + user_json_path)
                output += user_json_path + '\n'
                print_pyobj_to_json(initial_json, user_json_path)
    return HttpResponse(output, mimetype="application/json")
        
def full_pipline(request):
    """
    Does all the processing to import data generated on the phone
    """
    importAndroidData(request)
    generateAndroidOutput(request)
    fillUserFormCondition(request)
    correct_transcriptions(request)
    analyse_transcriptions(request)
    