import json, codecs
import os
import sys, subprocess
APP_ROOT = os.path.dirname(__file__)

def process_image(obj):
    obj.status = 'w'
    obj.save()
    stdoutdata, stderrdata = subprocess.Popen(['./ODKScan.run',
                      os.path.dirname(obj.template.image.path) + '/',
                      obj.image.path,
                      obj.output_path
                      ],
        cwd=os.path.join(APP_ROOT,
                         'ODKScan-core'),
        #env={'LD_LIBRARY_PATH':'/usr/local/lib'}, #TODO: This could cause problems on other systems, document or fix
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT).communicate()
    print >>sys.stdout, stdoutdata
    obj.processing_log = stdoutdata
    json_path = os.path.join(obj.output_path, 'output.json')
    if os.path.exists(json_path):
        #process_json_output(json_path)#Not sure I need this.
        obj.status = 'p'
    else:
        obj.status = 'e'
    obj.save()

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

def load_json_to_pyobj(path):
    fp = codecs.open(path, mode="r", encoding="utf-8")
    pyobj = json.load(fp, encoding='utf-8')
    fp.close()
    return pyobj

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