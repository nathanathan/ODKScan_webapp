import json, codecs

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