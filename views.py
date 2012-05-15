from django.http import HttpResponse, HttpResponseBadRequest
import sys, os, tempfile
from django.shortcuts import render_to_response, redirect
from django.core.context_processors import csrf

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

def save_transcription(request):
    c = {}
    c.update(csrf(request))
    if request.method == 'POST': # If the form has been submitted...
        row_dict = group_by_prefix(request.POST)
        temp_file = tempfile.mktemp()
        csvfile = open(temp_file, 'wb')
        dict_to_csv(row_dict.values(), csvfile)
        csvfile.close()
        response = HttpResponse(mimetype='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename=output.csv'
        fo = open(temp_file)
        response.write(fo.read())
        fo.close()
        return response
    else:
        return HttpResponseBadRequest("Only post requests please.")