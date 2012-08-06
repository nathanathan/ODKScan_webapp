from django.http import HttpResponse, HttpResponseBadRequest
from django.template import RequestContext, loader
from django.db.models import Max, Min, Count, Avg
from django.contrib.auth.models import User
from ODKScan_webapp.models import Template, FormImage, LogItem, UserFormCondition
import sys, os, re, tempfile
import json
import datetime
import ODKScan_webapp.utils as utils

from django.conf import settings
ANDROID_LOG_PATH = settings.ANDROID_LOG_PATH

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
excluded_users = ['user', 'test1', 'test2', 'test_final', 'T1', 'T2', 't98'] + android_excluded_users

def timedelta_in_seconds(time_delta):
    return (time_delta.microseconds + (time_delta.seconds + time_delta.days * 24 * 3600) * 10**6) * 1.0 / 10**6

def get_time_spent(log_items):
    time_spent_dict = {}
    startEndStamp = log_items.aggregate(Max('timestamp'), Min('timestamp'))
    if startEndStamp.get('timestamp__max'):
        time_spent = startEndStamp['timestamp__max'] - startEndStamp['timestamp__min']
        time_spent_dict['readable_time_spent'] = str(time_spent)
        time_spent_dict['seconds'] = (time_spent.microseconds + (time_spent.seconds + time_spent.days * 24 * 3600) * 10**6) * 1.0 / 10**6
        return time_spent_dict
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

def remove_outliers(log_items, max_time_difference=60):
    if len(log_items) < 2:
        return log_items
    groups = []
    cur_group = []
    groups.append(cur_group)
    previous_li = None
    #Segment the items by gaps of greater than max_time_difference
    for log_item in log_items.order_by('timestamp').all():
        if previous_li:
            if(timedelta_in_seconds(log_item.timestamp - previous_li.timestamp) > max_time_difference):
                cur_group = []
                groups.append(cur_group)
        cur_group.append(log_item)
        previous_li = log_item
    max_group = []
    #return the largest segment
    for group in groups:
        if len(group) > len(max_group):
            max_group = group
    return log_items.filter(timestamp__gte=max_group[0].timestamp, timestamp__lte=max_group[-1].timestamp)
    
def gen_form_stats(pyobj, ground_truth, filtered_log_items, condition):
    autofill = pyobj.get('autofill', True)
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
        field_log_items = filtered_log_items.filter(fieldName=field['name'])
        
        fieds_correctness_time[field['name']] = {
                                  'time_spent' : get_time_spent(remove_outliers(field_log_items)),
                                  'correctness' : correctness
                                  }
#        if fieds_correctness_time[field['name']]['time_spent']['seconds'] > 120:
#            from django.core import serializers
#            foobar = serializers.serialize('json', filtered_log_items.filter(fieldName=field['name']))
#            raise Exception('time bug')
        if 'transcription' in field:
            if field['transcription'] == gt_field['value']:
                if 'value' in field and autofill:
                    if str(field['value']) == gt_field['value']:
                        accuracy_matrix['correct_transcription']['correct_autofill']+=1
                    else:
                        accuracy_matrix['correct_transcription']['incorrect_autofill']+=1
                else:
                    accuracy_matrix['correct_transcription']['no_autofill']+=1
            else:
                if 'value' in field and autofill:
                    if str(field['value']) == gt_field['value']:
                        accuracy_matrix['incorrect_transcription']['correct_autofill']+=1
                    else:
                        accuracy_matrix['incorrect_transcription']['incorrect_autofill']+=1
                else:
                    accuracy_matrix['incorrect_transcription']['no_autofill']+=1
        else:
            if 'value' in field and autofill:
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

def genStats(userObject, form_image, pyobj, ground_truth):
    userStats = {}
    filtered_log_items = LogItem.objects.filter(user=userObject, formImage=form_image)
    condition = UserFormCondition.objects.get(user=userObject, formImage=form_image)
    userStats.update(gen_form_stats(pyobj, ground_truth, filtered_log_items, condition))
    autofill = pyobj.get('autofill', True)
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
        userStats.update(get_time_spent(filtered_log_items))

    backspaces = 0
    chars_added = 0
    total_lev_distance_traveled = 0
    for jsonField in pyobj['fields']:
        fieldName = jsonField['name']
        if jsonField['type'].startswith('select'):
            continue
        previous = ''
        if autofill:
            previous = str(jsonField.get('value', ''))
        for log_item in filtered_log_items.filter(fieldName=fieldName).order_by('timestamp').all():
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
    return userStats

def filter_fields(fields):
    allowedProps = ['name', 'label', 'transcription', 'type', 'value']
    for field in fields:
        for prop in field.keys():
            if prop not in allowedProps:
                field.pop(prop)
    return fields

def analyse_target(request, userName=None, formName=None):
    if not userName or not formName:
        return HttpResponse("no user/form name", mimetype="application/json")
    form_image = FormImage.objects.get(image__contains='/photo/'+formName)
    userObject = User.objects.get(username=userName)
    ground_truth = utils.load_json_to_pyobj(os.path.join(form_image.output_path, 'corrected.json'))
    json_path = os.path.join(os.path.join(form_image.output_path, 'users'), userObject.username, 'output.json')
    pyobj = utils.load_json_to_pyobj(json_path)
    kwargs = {
        'form_image' : form_image,
        'userObject' : userObject,
        'pyobj' : pyobj,
        'ground_truth' : ground_truth
    }
    userFormStats = genStats(**kwargs)
    filter_fields(pyobj['fields'])
    t = loader.get_template('analyseUserForm.html')
    c = RequestContext(request, {
                                 "userFormStats" : userFormStats,
                                 "ground_truth" : json.dumps(ground_truth, indent=4),
                                 "transciption" : json.dumps(pyobj, indent=4),
                                 })
    return HttpResponse(t.render(c))

def gen_analysis_dict(userFilter=(lambda k:True)):
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
                userObject = User.objects.get(username=user)
                if not userFilter(userObject):
                    continue
                json_path = os.path.join(os.path.join(form_image.output_path, 'users'), userObject.username, 'output.json')
                pyobj = utils.load_json_to_pyobj(json_path)
                kwargs = {
                    'form_image' : form_image,
                    'userObject' : userObject,
                    'pyobj' : pyobj,
                    'ground_truth' : ground_truth
                }
                user_dict[str(form_image)] = genStats(**kwargs)
                fi_dict[user] = fi_dict.get(user, {})
                fi_dict[user].update(user_dict)
    return fi_dict
    
def analyse(request):
    startswith = request.GET.get('startswith')
    def userFilter(userObject):
        if startswith:
            return userObject.username.startswith(startswith)
        return True
    analysis_dict = gen_analysis_dict(userFilter)
    format = request.GET.get('format', 'html')
    if format == 'json':
        data_array = listify(analysis_dict, ['user', 'form_image'])
        return HttpResponse(json.dumps(data_array, indent=4), mimetype="application/json")
    elif format == 'csv':
        temp_file = tempfile.mktemp()
        csvfile = open(temp_file, 'wb')
        data_array = listify(analysis_dict, ['user', 'form_image'])
        utils.dict_to_csv([flatten_dict(d) for d in data_array], csvfile)
        csvfile.close()
        response = HttpResponse(mimetype='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename=output.csv'
        fo = open(temp_file)
        response.write(fo.read())
        fo.close()
        return response    
    else:
        t = loader.get_template('analyseTranscriptions.html')
        c = RequestContext(request, {"formImages" : analysis_dict})
        return HttpResponse(t.render(c))



def to_pyobj(djm):
    pyobj = {}
    for field in djm.all():
        fieldout = {}
        fieldout['time_spent'] = str(field['end'] - field['start'])
        fieldout['modifications'] = field['modifications']
        pyobj[field['fieldName']] = fieldout
    return pyobj

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
            ct_field['type'] = field['type']
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

def add_ground_truth_length(correct_transcription):
    total_text_length = 0
    ct_fields = correct_transcription.get('fields')
    for ct_field in ct_fields:
        if ct_field['type'].startswith('select'):
            continue
        value_length = len(str(ct_field['value']))
        ct_field['value_length'] = value_length
        total_text_length += value_length
    correct_transcription['ground_truth_length'] = total_text_length

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
        add_ground_truth_length(correct_transcription)
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
            if action_type == 'text changed' or action_type == 'answer selected':
                user = fp_parse_dict['user']
                if user in excluded_users:
                    continue
                form = fp_parse_dict['form']
                showSegs = fp_parse_dict['showSegs'] if fp_parse_dict['showSegs'] else ""
                autofill = fp_parse_dict['autofill'] if fp_parse_dict['autofill'] else ""
                #For answer select and text changed the value is recorded in different columns
                previousValue = None if action_type == 'answer selected' else param1
                newValue = param1 if action_type == 'answer selected' else param2
                li_params = {
                            'user' : User.objects.get(username=user),
                            'url' : instance_path,
                            'formImage' : FormImage.objects.get(image__contains='/photo/'+form),
                            'view' : 'android-condition' + showSegs + autofill,
                            'fieldName' : os.path.split(question_path)[-1][:-3] if question_path else None,
                            'previousValue' : previousValue,
                            'newValue' : newValue,
                            'activity' : 'android-' + action_type,
                            'timestamp' : datetime.datetime.fromtimestamp(int(timestamp)*1./1000, utc),
                          }
                #output += str(li_params)
                LogItem.objects.create(**li_params).save()
        else:
            continue
            #raise Exception("Could not parse: " + str(instance_path))
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
            filtered_li = LogItem.objects.filter(formImage=form_image, user=user, activity__in=['android-text changed', 'android-answer selected'])
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
    print >>sys.stderr, "analyse"
    return analyse(request)
    