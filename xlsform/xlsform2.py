"""
XLSForm2 converts spreadsheets into forms for Collect 2.0
"""
import json, codecs, sys, os, re, warnings
import xlrd

def load_string(path, encoding="utf-8"):
    """
    Load the given file into a string.
    """
    fp = codecs.open(path, mode="r", encoding=encoding)
    result = fp.read()
    fp.close()
    return result

def merge_dictionaries(dict_a, dict_b, default_key = "default"):
    """
    Recursively merge two nested dicts into a single dict.
    When keys match their values are merged using a recursive call to this function,
    otherwise they are just added to the output dict.
    """
    if dict_a is None or dict_a == {}:
        return dict_b
    if dict_b is None or dict_b == {}:
        return dict_a
    
    if type(dict_a) is not dict:
        if default_key in dict_b:
            return dict_b
        dict_a = {default_key : dict_a}
    if type(dict_b) is not dict:
        if default_key in dict_a:
            return dict_a
        dict_b = {default_key : dict_b}
    
    all_keys = set(dict_a.keys()).union(set(dict_b.keys()))
    
    out_dict = dict()
    for key in all_keys:
        out_dict[key] = merge_dictionaries(dict_a.get(key), dict_b.get(key), default_key)
    return out_dict

def list_to_nested_dict(lst):
    """
    [1,2,3,4] -> {1:{2:{3:4}}}
    """
    if len(lst) > 1:
        return {lst[0] : list_to_nested_dict(lst[1:])}
    else:
        return lst[0]

def group_headers(worksheet):
    """
    For each row in the worksheet, group all keys with the group delimiter.
    For example:
    {"text/english": "hello", "text/french" : "bonjour"}
    becomes
    {"text": {"english": "hello", "french" : "bonjour"}.
    """
    GROUP_DELIMITER = '.'
    out_worksheet = list()
    for row in worksheet:
        out_row = dict()
        for key, val in row.items():
            tokens = key.split(GROUP_DELIMITER)
            new_key = tokens[0]
            new_value = list_to_nested_dict(tokens[1:] + [val])
            out_row = merge_dictionaries(out_row, { new_key : new_value })
        out_worksheet.append(out_row)
    return out_worksheet

def group_dictionaries(list_of_dicts, key, remove_key = True):
    """
    Takes a list of dictionaries and 
    returns a dictionary of lists of dictionaries with the same value for the given key.
    The grouping key is removed by default.
    If the key is not in any dictionary an empty dict is returned.
    """
    dict_of_lists = dict()
    for dicty in list_of_dicts:
        if key not in dicty: continue
        dicty_value = dicty[key]
        if remove_key: dicty.pop(key)
        if dicty_value in dict_of_lists:
            dict_of_lists[dicty_value].append(dicty)
        else:
            dict_of_lists[dicty_value] = [dicty]
    return dict_of_lists


def xls_to_dict(path_or_file):
    """
    Return a Python dictionary with a key for each worksheet
    name. For each sheet there is a list of dictionaries, each
    dictionary corresponds to a single row in the worksheet. A
    dictionary has keys taken from the column headers and values
    equal to the cell value for that row and column.
    """
    workbook = None
    if isinstance(path_or_file, basestring):
        workbook = xlrd.open_workbook(filename=path_or_file)
    else:
        workbook = xlrd.open_workbook(file_contents=path_or_file.read())
    result = {}
    for sheet in workbook.sheets():
        result[sheet.name] = []
        for row_idx in range(1, sheet.nrows):#Note that the header row_idx is skipped
            row_dict = {}
            for column_idx in range(0, sheet.ncols):
                #Only column header keys are striped.
                #Other cells are left alone incase whitespace is used for formating
                key = sheet.cell_value(0, column_idx).strip()
                key_type = sheet.cell_type(0, column_idx)
                if key_type in [xlrd.XL_CELL_ERROR, xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_DATE]:
                    raise Exception("Column header error at [column:" + column_idx + ']')
                value = sheet.cell_value(row_idx, column_idx)
                value_type = sheet.cell_type(row_idx, column_idx)
                if value_type is xlrd.XL_CELL_ERROR:
                    error_location = "[row :" + row_idx + ", column:" + column_idx + ']'
                    raise Exception("Cell error at " + error_location)
                if value_type is not xlrd.XL_CELL_EMPTY:
                    if value_type is xlrd.XL_CELL_NUMBER:
                        #Try to parse value as an int if possible.
                        int_value = int(value)
                        if int_value == value:
                            value = int_value
                    elif value_type is xlrd.XL_CELL_BOOLEAN:
                        value = bool(value)
                    elif value_type is xlrd.XL_CELL_DATE:
                        error_location = "[row :" + row_idx + ", column:" + column_idx + ']'
                        raise Exception("Cannot handle excel formatted date at " + error_location)
                    row_dict[key] = value
            result[sheet.name].append(row_dict)
    return result

def parse_prompts(worksheet):
    type_regex = re.compile(r"^(?P<type>\w+)(\s*(?P<param>.+))?$")
    names_used = set()
    promptTypeMap = {
        'select1':'select1',
        'select_one':'select1',
        'select':'select',
        'select_multiple':'select',
        'int':'int',
        'integer':'int',
        'string':'string',
        'text':'string',
        'markup':'markup',
        'note':'note',
        'tally':'tally',
    }
    prompt_stack = [{'prompts' : []}]
    for row, rowNum in zip(worksheet, range(len(worksheet))):
        if not 'type' in row:
            continue
        #Ensure names are all strings (i.e. not numbers)
        if 'name' in row:
            row['name'] = str(row['name'])
        row['type'] = row['type'].strip()
        type_parse = type_regex.search(row['type'])
        parse_dict = type_parse.groupdict()
        #Ignore case on types
        parse_dict['type'] = parse_dict['type'].lower()
        if parse_dict['type'] == 'begin':
            row['type'] = parse_dict['param']
            row['prompts'] = []
            prompt_stack.append(row)
            continue
        elif parse_dict['type'] == 'end':
            if prompt_stack[-1]['type'] == parse_dict['param']:
                top_prompt = prompt_stack.pop()
                prompt_stack[-1]['prompts'].append(top_prompt)
            else:
                rowString = '[row:' + str(rowNum) + ']'
                raise Exception(rowString + " Unmatched end statement.")
            continue
        else:
            row.update(parse_dict)
            #Name and type validation:
            if row['type'] in promptTypeMap:
                row['type'] = promptTypeMap[row['type']]
            else:
                rowString = '[row:' + str(rowNum) + ']'
                warnings.warn(rowString + " Unknown type: " + row['type'])
            if 'name' in row:
                if row['name'] in names_used:
                    rowString = '[row:' + str(rowNum) + ']'
                    warnings.warn(rowString + " Duplicate name found: " + row['name'])
                names_used.add(row['name'])
            prompt_stack[-1]['prompts'].append(row)
        continue
    if len(prompt_stack) != 1:
        print len(prompt_stack)
        raise Exception("Unmatched begin statement.")
    return prompt_stack.pop()['prompts']
    
def process_spreadsheet(path_or_file):
    """
    Process the given spreadshet by converting it to python dict/arrays
    and performing grouping on them (and possibly some dealiasing/validation) 
    so they come out as json that looks the way we want.
    """
    workbook = xls_to_dict(path_or_file)
    #Dealiasing?
    #Validation?
    for worksheet_name, worksheet in workbook.items():
        workbook[worksheet_name] = worksheet = group_headers(worksheet)
        if worksheet_name == 'survey':
            workbook[worksheet_name] = worksheet = parse_prompts(worksheet)
        elif worksheet_name == 'choices':
            workbook[worksheet_name] = worksheet = group_dictionaries(worksheet, 'list_name')
            
    return workbook

def spreadsheet_to_json(path_or_file, output_path):
    with codecs.open(output_path, mode="w", encoding="utf-8") as fp:
        json.dump(process_spreadsheet(path_or_file), fp=fp, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    """
    This code is for running XLSForm as a command line script.
    """import uuid
    argv = sys.argv
    #For debugging
    argv = [
            sys.argv[0],
            os.path.join(os.path.dirname(__file__), "test.xls"),
            os.path.join(os.path.dirname(__file__), "test.html"),
    ]
    if len(argv) < 3:
        print __doc__
        print 'Usage:'
        print argv[0] + ' path_to_XLSForm output_path'
    else:
        spreadsheet_to_json(argv[1], argv[2])
        print 'Conversion complete!'
        