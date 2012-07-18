from django.http import HttpResponse, HttpResponseBadRequest
from django.template import RequestContext, loader
from django.db.models import Max, Min, Count, Avg
from django.contrib.auth.models import User
from ODKScan_webapp.models import Template, FormImage, LogItem, UserFormCondition
import sys, os, re, tempfile
import json
import datetime
import ODKScan_webapp.utils as utils

ANDROID_LOG_PATH = '/home/nathan/Desktop/log26.sqlite'

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

def get_time_spent(log_items):
    time_spent_dict = {}
    startEndStamp = log_items.aggregate(Max('timestamp'), Min('timestamp'))
    if startEndStamp.get('timestamp__max'):
        time_spent = startEndStamp['timestamp__max'] - startEndStamp['timestamp__min']
        time_spent_dict['readable_time_spent'] = str(time_spent)
        time_spent_dict['seconds'] = (time_spent.microseconds + (time_spent.seconds + time_spent.days * 24 * 3600) * 10**6) * 1.0 / 10**6
        return time_spent
    else:
        return None

def compare_fields(field, the_truth):
    field_value = str(field.get('transcription', field.get('value', '')))
    if field['type'] == 'int':
        try:
            return abs(int(field_value) - int(the_truth['value']))
        except ZeroDivisionError:
            return 0.0
        except:
            return 0.0
    elif field['type'].startswith('select'):
        return (field_value == the_truth['value']) * 1
    else:
        return abs(levenshtein(field_value, the_truth['value']))
    
def gen_form_stats(pyobj, ground_truth, filtered_log_items, condition):
    fieds_correctness_time = {}
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
        correctness = compare_fields(field, gt_field)
        fieds_correctness_time[field['name']] = {
                                  'time_spent' : get_time_spent(filtered_log_items.filter(fieldName=field['name'])),
                                  'correctness' : correctness
                                  }
        
        if 'transcription' in field:
            if field['transcription'] == gt_field['value']:
                if 'value' in field and pyobj.get('autofill', True):
                    if str(field['value']) == gt_field['value']:
                        accuracy_matrix['correct_transcription']['correct_autofill']+=1
                    else:
                        accuracy_matrix['correct_transcription']['incorrect_autofill']+=1
                else:
                    accuracy_matrix['correct_transcription']['no_autofill']+=1
            else:
                if 'value' in field and pyobj.get('autofill', True):
                    if str(field['value']) == gt_field['value']:
                        accuracy_matrix['incorrect_transcription']['correct_autofill']+=1
                    else:
                        accuracy_matrix['incorrect_transcription']['incorrect_autofill']+=1
                else:
                    accuracy_matrix['incorrect_transcription']['no_autofill']+=1
        else:
            if 'value' in field and pyobj.get('autofill', True):
                if str(field['value']) == gt_field['value']:
                    accuracy_matrix['no_transcription']['correct_autofill']+=1
                else:
                    accuracy_matrix['no_transcription']['incorrect_autofill']+=1
            else:
                accuracy_matrix['no_transcription']['no_autofill']+=1
    stats = {
             'accuracy_matrix' : accuracy_matrix,
             'fieds_correctness_time' : fieds_correctness_time,
             'number_of_fields' : len(pyobj['fields']),
             }
    return stats

def gen_form_stats_orig(pyobj, ground_truth):
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
                    if str(field['value']) == gt_field['value']:
                        accuracy_matrix['correct_transcription']['correct_autofill']+=1
                    else:
                        accuracy_matrix['correct_transcription']['incorrect_autofill']+=1
                else:
                    accuracy_matrix['correct_transcription']['no_autofill']+=1
            else:
                if 'value' in field and pyobj.get('autofill', True):
                    if str(field['value']) == gt_field['value']:
                        accuracy_matrix['incorrect_transcription']['correct_autofill']+=1
                    else:
                        accuracy_matrix['incorrect_transcription']['incorrect_autofill']+=1
                else:
                    accuracy_matrix['incorrect_transcription']['no_autofill']+=1
        else:
            if 'value' in field and pyobj.get('autofill', True):
                if str(field['value']) == gt_field['value']:
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

def listify(dicty, level_labels):
    """
    Turn nested dictionaries a list of dictionaries.
    Each dictionary in the list will have a key for each level label.
    The value of that key will be the key the dictionary was nested under at the corresponding level.
    """
    if type(dicty) is not dict:
        raise Exception("Non dict")
    array = []
    for key, value in dicty.items():
        if len(level_labels) > 1:
            rows = listify(value, level_labels[1:])
            for row in rows:
                row[level_labels[0]] = key
            array += rows
        else:
            value[level_labels[0]] = key
            array.append(value)
    return array

def flatten_dict(dicty):
    if type(dicty) is not dict:
        raise Exception("Non dict")
    temp_dict = {}
    for key, value in dicty.items():
        if type(value) is dict:
            for nestedkey, nestedvalue in flatten_dict(dicty.pop(key)).items():
                temp_dict[key + '/' + nestedkey] = nestedvalue
    dicty.update(temp_dict)
    return dicty

def gen_analysis_dict():
    fi_dict = {}
    for form_image in FormImage.objects.all():
        if str(form_image)[0] == 'J':
            #Filter out practice forms
            continue
        ground_truth = utils.load_json_to_pyobj(os.path.join(form_image.output_path, 'corrected.json'))
        user_dir = os.path.join(form_image.output_path, 'users')
        user_list = []
        user_dict = {}
        if os.path.exists(user_dir):
            user_list = os.listdir(user_dir)
            for user in user_list:
                if user in excluded_users:
                    continue
                userStats = {}
                userObject = User.objects.get(username=user)
                #Filter by user properties here
                json_path = os.path.join(user_dir, user, 'output.json')
                pyobj = utils.load_json_to_pyobj(json_path)
                filtered_log_items = LogItem.objects.filter(user=userObject, formImage=form_image)
                condition = UserFormCondition.objects.get(user=userObject, formImage=form_image)
                userStats.update(gen_form_stats(pyobj, ground_truth, filtered_log_items, condition))
                if condition.tableView:
                    #TODO: Parse the save times
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
                        time_spent = (startEndStamp['timestamp__max'] - startEndStamp['timestamp__min'])/4
                        userStats['readable_time_spent'] = str(time_spent)
                        userStats['time_spent'] = (time_spent.microseconds + (time_spent.seconds + time_spent.days * 24 * 3600) * 10**6) / 10**6
                else:
                    if condition.formView:
                        userStats['form_view'] = True
                    startEndStamp = filtered_log_items.aggregate(Max('timestamp'), Min('timestamp'))
                    if startEndStamp.get('timestamp__max'):
                        time_spent = startEndStamp['timestamp__max'] - startEndStamp['timestamp__min']
                        userStats['readable_time_spent'] = str(time_spent)
                        userStats['time_spent'] = (time_spent.microseconds + (time_spent.seconds + time_spent.days * 24 * 3600) * 10**6) / 10**6
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
    return fi_dict
    
def analyse_transcriptions(request):
    data_array = listify(gen_analysis_dict(), ['user', 'form_image'])
    return HttpResponse(json.dumps(data_array, indent=4), mimetype="application/json")
    t = loader.get_template('analyseTranscriptions.html')
    c = RequestContext(request, {"formImages" : gen_analysis_dict()})
    return HttpResponse(t.render(c))

def generate_csv(request):
    temp_file = tempfile.mktemp()
    csvfile = open(temp_file, 'wb')
    data_array = listify(gen_analysis_dict(), ['user', 'form_image'])
    utils.dict_to_csv([flatten_dict(d) for d in data_array], csvfile)
    csvfile.close()
    response = HttpResponse(mimetype='application/octet-stream')
    response['Content-Disposition'] = 'attachment; filename=output.csv'
    fo = open(temp_file)
    response.write(fo.read())
    fo.close()
    return response

def to_pyobj(djm):
    pyobj = {}
    for field in djm.all():
        fieldout = {}
        fieldout['time_spent'] = str(field['end'] - field['start'])
        fieldout['modifications'] = field['modifications']
        pyobj[field['fieldName']] = fieldout
    return pyobj

#def analyse_group(request, username=None):
#    fi_dict = {}
#    for form_image in FormImage.objects.all():
#        user_dir = os.path.join(form_image.output_path, 'users')
#        user = username
#        json_path = os.path.join(user_dir, user, 'output.json')
#        if os.path.exists(json_path):
#            pyobj = load_json_to_pyobj(json_path)
#            userStats = gen_form_stats(pyobj)
#            userObject = User.objects.get(username=user)
#            startEndStamp = LogItem.objects.filter(user=userObject, formImage=form_image).aggregate(Max('timestamp'), Min('timestamp'))
#            if startEndStamp.get('timestamp__max'):
#                userStats['time_spent'] = str(startEndStamp['timestamp__max'] - startEndStamp['timestamp__min'])
#            userStats['fields_logitems'] = to_pyobj(LogItem.objects.filter(user=userObject, formImage=form_image).values('fieldName').annotate(modifications=Count('pk'), end=Max('timestamp'), start=Min('timestamp')))
#            fi_dict[str(form_image)] = userStats
#    return HttpResponse(json.dumps(fi_dict), mimetype="application/json")

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
        
        add_to_correct_transcription(correct_transcription, utils.load_json_to_pyobj(os.path.join(form_image.output_path, 'output.json')))
        
        user_dir = os.path.join(form_image.output_path, 'users')
        user_list = []
        if os.path.exists(user_dir):
            user_list = os.listdir(user_dir)
            for user in user_list:
                if user in excluded_users:
                    continue
                json_path = os.path.join(user_dir, user, 'output.json')
                pyobj = utils.load_json_to_pyobj(json_path)
                add_to_correct_transcription(correct_transcription, pyobj)
        fi_dict[str(form_image)] = correct_transcription
        utils.print_pyobj_to_json(correct_transcription, os.path.join(form_image.output_path, 'corrected.json'))
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
                pyobj = utils.load_json_to_pyobj(json_path)
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

ZERO = datetime.timedelta(0)
HOUR = datetime.timedelta(hours=1)

class UTC(datetime.tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

utc = UTC()

#Also need to genrate output.json
def importAndroidData(request):
    output = ''
    #Create the log items
    import sqlite3, time
    conn = sqlite3.connect(ANDROID_LOG_PATH)
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
                            'timestamp' : datetime.datetime.fromtimestamp(int(timestamp)*1./1000, utc),
                          }
                #print question_path
                LogItem.objects.create(**li_params).save()
        else:
            raise Exception("Could not parse: " + str(instance_path))
    return HttpResponse(output, mimetype="application/json")
        
def generateAndroidOutput(request):
    output = ''
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
                initial_json = utils.load_json_to_pyobj(path_to_initial_json)
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
                utils.print_pyobj_to_json(initial_json, user_json_path)
    return HttpResponse(output, mimetype="application/json")

def parseSaveLogItems(request):
    """
    This creates additional log items for the unparsed log items generated by save_transcription.
    """
    out = ''
    for li in LogItem.objects.filter(activity='save_transcriptions'):
        if not li.forms:
            continue
        if len(li.forms) == 0:
            continue
        for form in li.forms.split(','):
            formField = form.split('-')
            formId = formField[0]
            try:
                li_params = {
                    'user' : li.user,
                    'url' : li.url,
                    'activity': li.activity,
                    'formImage' : FormImage.objects.get(id=formId),
                    'view' : li.view,
                    #'fieldName' : formField[1],
                    #'newValue' : param2,
                    'timestamp' : li.timestamp,
                 }
                LogItem.objects.create(**li_params).save()
            except:
                out += form
    return HttpResponse(out, mimetype="application/json")

def full_pipeline(request):
    """
    Does all the processing to import data generated on the phone
    """
    print >>sys.stderr, "parseSaveLogItems"
    parseSaveLogItems(request)
    #Don't forget to syncDB
    print >>sys.stderr, "importAndroidData"
    importAndroidData(request)
    print >>sys.stderr, "generateAndroidOutput"
    generateAndroidOutput(request)
    print >>sys.stderr, "fillUserFormCondition"
    fillUserFormCondition(request)
    print >>sys.stderr, "correct_transcriptions"
    correct_transcriptions(request)
    print >>sys.stderr, "analyse_transcriptions"
    return analyse_transcriptions(request)
    