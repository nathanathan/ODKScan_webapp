$(document).ready(function () {

var _ = window._;
var XLSX = window.XLSX;
var XLSXConverter = window.XLSXConverter;
var Handlebars = window.Handlebars;
var MyJSZip = window.MyJSZip;
var html2canvas = window.html2canvas;

var removeEmptyStrings = function(rObjArr){
    var outArr = [];
    _.each(rObjArr, function(row){
        var outRow = Object.create(row.__proto__);
        _.each(row, function(value, key){
            if(_.isString(value) && value.trim() === "") {
                return;
            }
            outRow[key] = value;
        });
        if(_.keys(outRow).length > 0) {
            outArr.push(outRow);
        }
    });
    return outArr;
};

var to_json = function(workbook) {
    var result = {};
    _.each(workbook.SheetNames, function(sheetName) {
        var rObjArr = XLSX.utils.sheet_to_row_object_array(workbook.Sheets[sheetName]);
        rObjArr = removeEmptyStrings(rObjArr);
        if(rObjArr.length > 0){
    		result[sheetName] =  rObjArr;
		}
	});
	return result;
};

var processXLSX = function(data, filename, callback){
    try {
        var xlsx = XLSX.read(data, {type: 'binary'});
        var jsonWorkbook = to_json(xlsx);
        var processedWorkbook = XLSXConverter.processJSONWorkbook(jsonWorkbook);
        processedWorkbook.filename = filename;
        
        renderForm(processedWorkbook, callback);
        
        _.each(XLSXConverter.getWarnings(), function(warning){
            var $warningEl = $("<p>");
            $warningEl.text(warning);
            $("#warnings").append($warningEl);
        });
    } catch(e) {
        var $errorEl = $("<p>");
        $errorEl.text(String(e));
        $("#errors").append($errorEl);
        throw e;
    }
};

$('.xlsxfile').change(function(evt) {
	evt.stopPropagation();
	evt.preventDefault();
    
    //Clear the warnings and errors:
    $('#errors').empty();
    $('#warnings').empty();
    $('#download').empty();
    
	var files = evt.target.files;
	var file = files[0];
    if(file.name.slice(-3) === "xls"){
        $("#errors").append("<p>Sorry, XLS files are not supported.<br />You can convert your XLS file to XLSX using libreOffice or Google Docs.</p>");
        return;
    }
    
	var reader = new FileReader();
    reader.onload = function(e) {
		var data = e.target.result;
        processXLSX(data, file.name);
	};
    try {
        reader.readAsBinaryString(file);
    } catch(e) {
        $("#errors").append("<p>Could not read file.</p>");
        throw e;
    }
    //Clear the file input so the form can be updated:
    $('.xlsxfile').val("");
});

//Handlebars compilation of the templates at the bottom of index.html:
var formTemplate = Handlebars.compile($("#form-template").html());

// compile and register the "element" partial template
var fieldRowTemplate = Handlebars.compile($("#field-row-template").html());
Handlebars.registerPartial("fieldRow", fieldRowTemplate);

var fieldColumnTemplate = Handlebars.compile($("#field-column-template").html());
Handlebars.registerPartial("fieldColumn", fieldColumnTemplate);

var segmentsTemplate = Handlebars.compile($("#segments-template").html());
Handlebars.registerPartial("segments", segmentsTemplate);

var segmentTemplate = Handlebars.compile($("#segment-template").html());
Handlebars.registerPartial("segment", segmentTemplate);

var makeQRCodeImg = function(data, size) {
    var defaultSize = (1 + Math.floor(data.length / 40)) * 96;
    size = size ? size : defaultSize;console.log(size, defaultSize);
    if(size < defaultSize) {
        alert("Warning, there is a qrcode constrained to a size smaller " +
            "than recommended for the amount of data it contains.");
    }
    return '<img width=' + size + ' height=' + size + ' src="' +
        $('<canvas width=' + size + ' height=' + size + '>').qrcode({
            width: size,
            height: size,
            text: data
        }).get(0).toDataURL('image/jpeg') + '"></img>';
};
Handlebars.registerHelper("qrcodeImg", function(qrcodeSpec) {
    return new Handlebars.SafeString(makeQRCodeImg(qrcodeSpec.data, qrcodeSpec.size));
});

var typeAliases = {
    "text" : "string",
    "integer" : "int",
    "select_one" : "select1",
    "select_multiple" : "select"
};

var renderForm = function(formJSON, callback){
    console.log("Rendering...", formJSON);

    var alignment_radius =  _.findWhere(formJSON.settings, {
        setting: 'alignment_radius'
    });
    alignment_radius = alignment_radius ? alignment_radius.value : 2.0;
    
    
    var classifierSpecs = {};
    classifierSpecs.bubble = {
        "classification_map": {
             "empty": false
        },
        "default_classification": true,
        "training_data_uri": "bubbles",
        "classifier_height": 16,
        "classifier_width": 14,
        "alignment_radius": alignment_radius,
        "advanced": {
             "flip_training_data": true
        }
    };
    classifierSpecs.checkbox = _.extend({}, classifierSpecs.bubble, {
        "training_data_uri": "square_checkboxes",
    });
    //Experimental
    classifierSpecs.number = {
        "classification_map": {
          "1": "1",
          "2": "2",
          "3": "3",
          "4": "4",
          "5": "5",
          "6": "6",
          "7": "7",
          "8": "8",
          "9": "9",
          "0": "0"
        },
        "default_classification": true,
        "training_data_uri": "numbers",
        "classifier_height": 28,
        "classifier_width": 20,
        "alignment_radius": alignment_radius,
        "advanced": {
             "flip_training_data": false,
             "eigenvalues" : 13
        }
    };
    
    var defaultScanJSON = {
        height: 1088,
        width: 832,
        classifier : classifierSpecs.bubble
    };

    //nameCounter is used to generate unique names for unnamed elements.
    var nameCounter = 0;
    
    //The field map will be populated by preprocess in order to
    //provide an easy way to reference the augmented JSON for each field
    //for use in the Scan JSON output.
    var fieldMap = {};
    
    //Preprocess does the following:
    //-Attach items.
    //-Annotate JSON with other data needed further down the pipeline.
    //-Rename some the types to the types Scan uses.
    //-Generate a field map for retrieving a field's JSON by it's name.
    var preprocess = function(fields) {
        _.each(fields, function(field) {
            if('prompts' in field){
                preprocess(field.prompts);
                return;
            }
            field.type = field.type.toLowerCase();
            
            //ensure that names and labels are strings rather than numbers
            if("label" in field) {
                field.label = "" + field.label;
            }
            if("name" in field) {
                field.name = "" + field.name;
            }
            if(!('name' in field)){
                field.name = "autogenerated_name_" + nameCounter;
                nameCounter++;
            }
            
            //Map from XLSForm types to internal type names that are closer
            //to XForm types.
            if(field.type in typeAliases) {
                field.__originalType__ = field.type;
                field.type = typeAliases[field.type];
            }
            
            if(field.type.match(/string|int|decimal/)){
                field.segments = [{
                    rows: _.range(field.rows ? field.rows : 0)
                }];
            } else if(field.type.match(/select/)){
                if(field.type === "select") {
                    field.classifier = classifierSpecs.checkbox;
                }
                if(!(field.param in formJSON.choices)) {
                    $("#errors").append("<p>Missing choices: " + field.param + "</p>");
                    return;
                }
                field.segments = [{
                    items : _.map(formJSON.choices[field.param], function(item){
                        if(field.type === "select1") {
                            item.objectClass = "bubble";
                        } else {
                            item.objectClass = "checkbox";
                        }
                        return item;
                    })
                }];
            } else if(field.type.match(/tally/)){
                field.segments = [{
                    items :  _.map(_.range(parseInt(field.param, 10)), function(rIdx){
                        return {
                            objectClass: "bubble"
                        };
                    })
                }];
            } else if(field.type.match(/bub_num/)){
                field.segments = _.map(_.range(parseInt(field.param, 10)), function(){
                    return { };
                });
                _.each(field.segments, function(segment){
                    segment.items = _.map(_.range(0, 10), function(rIdx){
                        return {
                            value: rIdx,
                            label: "" + rIdx,
                            class: "vertical",
                            objectClass: "bubble"
                        };
                    });
                });
                field.labels = _.map(_.range(0, 10), function(rIdx){
                    return "" + rIdx;
                });
                field.__combineSegments__ = true;
                //Makes scan combine all the values
                //rather than putting a space between them.
                field.delimiter = "";
                field.type = "int";
            } else if(field.type.match(/bub_word/)){
                //Note the space bubble.
                //It seems like it would be better to have an empty
                //column be a space but the logic for that would be messier.
                var alphabet = (' abcdefghijklmnopqrstuvwxyz').split('');
                field.segments = _.map(_.range(parseInt(field.param, 10)), function(){
                    return { };
                });
                _.each(field.segments, function(segment){
                    segment.items = _.map(alphabet, function(letter){
                        return {
                            value: letter,
                            label: letter,
                            class: "vertical",
                            objectClass: "bubble"
                        };
                    });
                });
                field.labels = _.map(alphabet, function(letter){
                    return letter;
                });
                field.__combineSegments__ = true;
                //Makes scan combine all the values
                //rather than putting a space between them.
                field.delimiter = "";
                field.type = "string";
            } else if(field.type.match(/qrcode/)){
                field.segments = [{
                    qrcode : {
                        data : field.param,
                        size : field.qrcode_size
                    }
                }];
            } else if(field.type.match(/writein_num/)){
                //Experimental
                field.segments = [{
                    items: _.map(_.range(field.param), function(){
                        return { objectClass: "number" };
                    })
                }];
                field.delimiter = "";
                field.classifier = classifierSpecs.number;
                //This is a string to get around the digit limit.
                field.type = "string";
            }
            
            fieldMap[field.name] = _.omit(field, ['segments', 'labels']);
        });
    };
    
    /**
     * Create a Scan JSON form definition based on the contents of the passed
     * in HTML form image element.
     * The HTML layout is used to determine the coordinates of form elements.
     **/
    var generateScanJSON = function($formImage){
        var formDef = _.clone(defaultScanJSON);

        //Generate the formDef json using the HTML.
        var baseOffset = $formImage.offset();
        
        //Hack to get non-rounded value of partial pixel offsets:
        //Nevermind, doesn't work in FF
        //baseOffset.left = parseFloat($('.formImage').css("margin-left"), 10);
        
        formDef.fields = $formImage.find('.scanField').map(function(idx, fieldEl){
            var generateSegmentJSON = function(idx, segmentEl){
                var $segment = $(segmentEl);
                var segAbsOffset = $segment.offset();
                var segOffset = {
                    top: segAbsOffset.top - baseOffset.top,
                        //(parseInt($segment.css("border-top-width"), 10)  / 2),
                    left: segAbsOffset.left - baseOffset.left
                        //(parseInt($segment.css("border-left-width"), 10) / 2)
                };
                var items = $segment
                    .find('.classifiableObject')
                    .map(function(idx, itemEl){
                    var $item = $(itemEl);
                    var itemAbsOffset = $item.offset();
                    //I think an ideal solution would be to use floats
                    //throughout the pipeline.
                    //Text dimensions (em/pt) cause issues because they lead to
                    //partial pixel measurements that cause rounding errors.
                    var itemOffset = {
                        top: itemAbsOffset.top - segAbsOffset.top +
                            ($item.innerHeight() + $item.outerHeight()) / 4,
                        left: itemAbsOffset.left - segAbsOffset.left +
                            ($item.innerWidth() + $item.outerWidth()) / 4,
                    };
                    var output = {
                        item_x: itemOffset.left,
                        item_y: itemOffset.top
                    };
                    //This should remove any html markup.
                    var label = $item.parent().children('label').text();
                    var value = $item.parent().data('value');
                    //Ignore falsy values except 0.
                    if(!_.isUndefined(label) && label !== "") {
                        output.label = label;
                    }
                    if(!_.isUndefined(value) && value !== "") {
                        output.value = value;
                    }
                    return output;
                }).toArray();
                var segment = {
                    //Need to fix this...
                    align_segment: true,
                    segment_x: segOffset.left,
                    segment_y: segOffset.top,
                    segment_width: ($segment.innerWidth() +
                        $segment.outerWidth()) / 2,
                    segment_height: ($segment.innerHeight() +
                        $segment.outerHeight()) / 2
                };
                if(items.length > 0) {
                    segment.items = items;
                }
                return segment;
            };
            var segments;
            var $field = $(fieldEl);
            var fieldName = $field.data('name');
            if(_.isUndefined(fieldName)){
                console.error("Skipping field with no name.", $field);
                return null;
            }
            var out = fieldMap[fieldName];
            
            if(out.type === "markup"){
                return null;
            } else if(out.__combineSegments__) {
                //All the segments of bub_num/bub_word prompts are
                //combined into one because it shows up better when transcribing
                //and because segment alignment is bad at skinny segments.
                segments = [ generateSegmentJSON(0,
                    $field.find('.segment-container').find('tr').get(0)) ];
            } else {
                segments = $field
                    .find('.segment')
                    .map(generateSegmentJSON)
                    .toArray();
            }
            
            if(segments.length > 0) {
                out.segments = segments;
            }
            
            //The label value from the HTML is used for two reasons:
            //1. It allows the label to be edited on the page.
            //2. It strips any html fomating used.
            out.label = $field.find('label').first().text();

            return out;
        }).toArray();
                    
        //remove nulls
        formDef.fields = _.compact(formDef.fields);
        return formDef;
    };

    var generateFormPageHTML = function($el, formJSON){
        //Generate the form image as HTML.
        var title =  _.findWhere(formJSON.settings, {setting: 'form_title'});
        title = title ? title.value : "";
        var font =  _.findWhere(formJSON.settings, {setting: 'font'});
        font = font ? font.value : "";
        var title_font =  _.findWhere(formJSON.settings, {setting: 'title_font'});
        title_font = title_font ? title_font.value : "";
        
        $el.html(formTemplate({
            prompts: formJSON.survey,
            title: title,
            font: font,
            title_font: title_font
        }));
        
        //Fiducal replacement functionality
        var $fiducials = $el.find('img');
        $fiducials.on('dragover', function(e){
            e.stopPropagation();
            e.preventDefault();
            e.originalEvent.dataTransfer.dropEffect = 'copy';
        });
        $fiducials.on('drop', function(e){
            e.stopPropagation();
            e.preventDefault();
            var files = e.originalEvent.dataTransfer.files;
            
            var reader = new FileReader();
            
            var $targetEl = $(e.target);
            
            reader.onload = function(e) {
                $targetEl.attr('src', e.target.result);
                generateZip();
            };
            reader.readAsDataURL(files[0]);
        });
        
        $el.find('label').on('click', function(e) {
            var newLabel = prompt("Enter new label:");
            if(!newLabel) return;
            $(e.target).html(newLabel);
            generateZip();
        });

        $el.find('.qrcode').on('click', function(e) {
            //Size is preserved so the layout doesn't change.
            var currentImgSize = $(e.target).closest('img').width();
            var newData = prompt("Enter new data to encode:");
            if(!newData) return;
            $(e.target)
                .closest('.qrcode')
                .html(makeQRCodeImg(newData, currentImgSize));
            generateZip();
        });

        //Set some of the dimensions using the defaultScanJSON:
        $el.height(defaultScanJSON.height);
        $el.width(defaultScanJSON.width);
        
        //Set the classified object sizes based on the specs
        _.each(['bubble', 'checkbox'], function(name){
            var classifier = classifierSpecs[name];
            var coHeight = Math.round(
                classifier.classifier_height * 0.64);
            var coWidth = Math.round(
                classifier.classifier_width * 0.64);
            $el.find(".classifiableObject." + name).height(coHeight);
            $el.find(".classifiableObject." + name).width(coWidth);
        });
        (function(classifer){
            var coHeight = Math.round(
                classifer.classifier_height * 1.15);
            var coWidth = Math.round(
                classifer.classifier_width * 1.15); console.log(classifer);
            var $numObjects = $el.find(".classifiableObject.number");
            $numObjects.height(coHeight);
            $numObjects.width(coWidth);
            _.each(_.range(6), function(idx){
                $numObjects.append('<div class="guide-dot">');
            });
        }(classifierSpecs.number));
        
        //round the bubbles
        $el.find(".bubble").css('borderRadius', Math.round(
                classifierSpecs.bubble.classifier_width * 0.64) / 2);
        
        //Ensure the bub_num and bub_word widgets line up:
        $el.find(".vertical")
            .height(classifierSpecs.bubble.classifier_height + 2);
        return $el;
    };
    
    preprocess(formJSON.survey);console.log(fieldMap);
    //partition the formJSON into multiple objects
    //by pagebreaks
    var pages = _.reduce(formJSON.survey, function(memo, row){
        if(row.type === "pagebreak"){
            memo.push([]);
        } else {
            memo[memo.length - 1].push(row);
        }
        return memo;
    }, [[]]);
    
    pages = _.filter(pages, function(page){
        return page.length !== 0;
    });

    $('.fContainer').empty();
    
    var generatedHTMLPages = _.map(pages, function(page, pageIdx){
        var $pageHTML = $('<div class="formImage">');
        $('.fContainer').append($pageHTML);
        generateFormPageHTML($pageHTML, _.extend({}, formJSON, {
            survey: page
        }));
        return $pageHTML;
    });
    
    /**
     * Generate a zip including the Scan JSON form def and freshly created jpg images
     * based on the current state of the HTML form pages.
     **/
    var generateZip = function(){
        $('#download').html("<div>Genenrating template...</div>");
        $('.outImgs').empty();
        var zip = new MyJSZip();
        var pathMap = {};
        $.when.apply(null, _.map(generatedHTMLPages, function($pageHTML, pageIdx){
            var promise = $.Deferred();
            
            var formDef = generateScanJSON($pageHTML);
            
            //outImgs are used for printing...
            //This is kept separate from the src setting below
            //so its inserted in page order.
            var $img = $('<img>');
            $('.outImgs').append($img);
            
            //Generate the form image from the html.
            html2canvas([$pageHTML.get(0)], {
                onrendered: function(canvas) {
                    var dataURL = canvas.toDataURL('image/jpeg');
                    var formName = formJSON.filename ? formJSON.filename.slice(0,-5) : "template";
                    var prefix = _.reduce(_.range(pageIdx), function(memo){
                        return memo + "nextPage/";
                    }, formName + "/");
                    
                    $img.attr('src', dataURL);
                    
                    pathMap[prefix + "template.json"] = formDef;
                    pathMap[prefix + "form.jpg"] = dataURL;
                    
                    zip.file(prefix + "template.json",
                        JSON.stringify(formDef,null,2));
                    zip.file(prefix + "form.jpg",
                        dataURL.substr("data:image/jpeg;base64,".length),
                        { base64: true });
                    
                    promise.resolve();
                }
            });
            return promise;
        })).then(function(){
            var zipped = zip.generate({
                type:'blob'
            });
            $('#download').html($('#download-notice').html());
            var $downloadBtn = $('#download').find('.download');
            $downloadBtn.attr('href', window.URL.createObjectURL(zipped));
            $downloadBtn.attr('download', "template.zip");
            if(!_.isUndefined(callback)){
                callback(pathMap);
            }
        });
    };
    
    $('#download').html("<div>Genenrating template...</div>");
    
    //Wait for the DOM stuff before generating the JSON
    window.setTimeout(generateZip, 500);
};
   
//$.getJSON('test.json', renderForm);
window.app = {
    renderForm : renderForm,
    processXLSX : processXLSX
};

});
