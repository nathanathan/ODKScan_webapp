"""
form_creator.py take an XLSForm (or rather something similar for the time being)
and uses it to create a JSON template and form image for use with ODK Scan.
"""
import json, codecs, sys, os, re
import xlsform2
import xml.dom.minidom

def separate_markup(fields):
    #This function separates out markup fields
    #so they are not used for scanning or in collect
    markup = []
    non_markup = []
    for field in fields:
        if field['type'] == 'markup':
            markup.append(field)
        else:
            non_markup.append(field)
    return non_markup, markup

def make_json_template(xlsform_obj,
                       form_height = 1076, #Using letter height
                       form_width = 832,
                       margin_y = 100,
                       margin_x = 40,
                       ):
    """
    Create a json template from the xlsform json
    by adding location information to the fields.
    """
    output = {
        "height": form_height,
        "width": form_width,
        "classifier": {
                "classification_map": {
                     "empty": False
                },
                "default_classification": True,
                "training_data_uri": "bubbles",
                "classifier_height": 18,
                "classifier_width": 18,
                "advanced": {
                     "alignment_radius": 4.0,
                     "flip_training_data": True
                }
        }
    }
    output.update(xlsform_obj.get('settings', {})[0])
    choice_lists = xlsform_obj['choices']
    
    #The functions below are defined inside this function
    #so they can access the choice_lists and form properties
    #without me having the pass them around.
    def generate_items(item_list,
                      segment,
                      item_width = output["classifier"]["classifier_width"],
                      item_label_width = 0,
                      item_height = output["classifier"]["classifier_height"],
                      row_one_left_margin = 400,
                      base_margin = 14,
                      ):
        if len(item_list) > 3:
            row_one_left_margin = 999999 #skip the first row
        left_margin = row_one_left_margin
        y_offset = 0
        out_item_list = []
        if segment['segment_width'] - 2 * base_margin < item_width + item_label_width:
            raise Exception('Cannot fit choices in segment. Do you have a group more than 5 questions?')
        choice_idx = 0
        while choice_idx < len(item_list):
            y_offset += item_height
            segment['segment_height'] = y_offset + item_height
            x_coords = range(left_margin + item_label_width,
                           segment['segment_width'] - base_margin - item_width,
                           item_width + item_label_width)
            for x in x_coords:
                if choice_idx == len(item_list): return out_item_list
                choice = item_list[choice_idx]
                choice_idx += 1
                choice.update({
                      "item_x": x + item_width/2,
                      "item_y": y_offset
                })
                out_item_list.append(choice)
            left_margin = base_margin
        return out_item_list
    
    def generate_field(field, segment):
        #Validate name:
        field_name = field.get('name')
        if field_name:
            try:
                xml.dom.minidom.parseString('<' + field_name + ' />')
            except:
                raise Exception('Invalid name: ' + field_name + '\nNames must be valid xml tag names.')
        
        if field['type'] == 'select' or field['type'] == 'select1':
            list_name = field["param"]
            if list_name not in choice_lists:
                raise Exception("List name not in choices sheet: " +
                                list_name )
            field['items'] = generate_items(choice_lists[list_name],
                                           segment,
                                           item_label_width=70)
        elif field['type'] == 'tally':
            amount_str = field["param"]
            amount = 40
            try:
                amount = int(amount_str)
            except:
                pass
            field['type'] = 'int'
            field['items'] = generate_items([{} for x in range(amount)],
                                           segment)
        elif field['type'] == "string":
            pass
        elif field['type'] == "int":
            pass
        else:
            pass
        min_height = field.get('min_height', segment['segment_height'])
        if min_height > segment['segment_height']:
            segment['segment_height'] = min_height
        field['segments'] = [segment]
        return field
        
    def generate_fields(in_fields, segment):
        """
        Generate field segments to fill the page.
        The segment param sets the starting point and width.
        Height is variable.
        A tuple with remaining fields is returned if the page height is overflowed.
        """
        fields = []
        for field, idx in zip(in_fields, range(len(in_fields))):
            if segment["segment_y"] > (form_height - margin_y):
                #This is where we split pages.
                #I don't think this interferes with the recusive call to generate_fields
                #because I think segment_y is the same at the top level call,
                #so this condition will only be triggered from there.
                #I added an assert to be sure.
                return fields, in_fields[idx:]
            if field['type'] in ['group', 'block']:
                idx = 0
                col_width = float(segment["segment_width"]) / len(field['prompts'])
                col_segments = []
                for field in field['prompts']:
                    col_segment = {
                      "segment_x": int(segment['segment_x'] + round(idx * col_width)),
                      "segment_y": segment["segment_y"],
                      "segment_width": int(round(col_width)),
                      "segment_height": 30, #default height is not static
                      "row_segments" : []
                    }
                    col_segments.append(col_segment)
                    if field['type'] in ['group', 'block']:
                        row_fields, remaining_fields = generate_fields(field['prompts'], col_segment)
                        assert not remaining_fields
                        fields += row_fields
                        col_segment['row_segments'] = [ f['segments'][0] for f in row_fields ]
                    else:
                        field_json = generate_field(field, col_segment)
                        fields.append(field_json)
                    idx += 1
                #Now set the Y offsets and heights of the segments
                max_bottom_y = segment['segment_y']
                for col_segment in col_segments:
                    row_segments = col_segment.get('row_segments')
                    bottom_segment = row_segments[-1] if row_segments else col_segment
                    bottom_y = bottom_segment['segment_height'] + bottom_segment['segment_y']
                    if max_bottom_y < bottom_y:
                        max_bottom_y = bottom_y                            
                for col_segment in col_segments:
                    row_segments = col_segment.pop('row_segments')
                    bottom_segment = row_segments[-1] if row_segments else col_segment
                    bottom_segment['segment_height'] = max_bottom_y - bottom_segment['segment_y']
                segment['segment_y'] = max_bottom_y
            else:
                field_segment = segment.copy()
                #remove extra junk from the segment
                if 'row_segments' in field_segment:
                    del field_segment['row_segments']
                field_json = generate_field(field, field_segment)
                if not field_json:
                    continue
                else:
                    fields.append(field_json)
                segment['segment_y'] = field_segment['segment_y'] + field_segment['segment_height']
            pass
        return fields, None
        
    pages = []
    remaining_fields = xlsform_obj['survey']
    page_number = 0
    while True:
        page_number += 1
        fields_so_far, remaining_fields = generate_fields(remaining_fields, {
                                                                   'segment_x' : margin_x,
                                                                   'segment_y' : margin_y,
                                                                   'segment_width' : form_width - margin_x * 2,
                                                                   'segment_height' : 20
                                                                   })
        page = output.copy()
        page['fields'], page['markup'] = separate_markup(fields_so_far)
        page['page_number'] = page_number
        pages.append(page)
        if not remaining_fields:
            break
    return pages
    
def create_form(path_or_file, output_path):
    xlsform_obj = xlsform2.process_spreadsheet(path_or_file)
    pages = make_json_template(xlsform_obj)
    cur_output_path = output_path
    paths = []
    for page in pages:
        if not os.path.exists(cur_output_path):
            os.makedirs(cur_output_path)
        paths.append(cur_output_path)
        with codecs.open(os.path.join(cur_output_path, 'template.json'), mode="w", encoding="utf-8") as fp:
            json.dump(page, fp=fp, ensure_ascii=False, indent=4)
        cur_output_path = os.path.join(cur_output_path, 'nextPage')
    return paths
    
if __name__ == "__main__":
    argv = sys.argv
    #For debugging
    argv = [
            sys.argv[0],
            os.path.join(os.path.dirname(__file__), "test.xlsx"),
            os.path.join(os.path.dirname(__file__), "test_output", "test"),
    ]
    if len(argv) < 3:
        print __doc__
        print 'Usage:'
        print argv[0] + ' path_to_XLSForm output_path'
    else:
        create_form(argv[1], argv[2])
        print 'Conversion complete!'
