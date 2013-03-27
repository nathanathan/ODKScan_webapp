function getParameter(paramName, defaultValue) {
    var searchString = window.location.search.substring(1);
    searchString = searchString ? searchString : window.location.hash.substring(2);
    var params = searchString.split('&');
    for (var i = 0; i < params.length; i++) {
        var val = params[i].split('=');
        if (val[0] === paramName) {
            return decodeURI(val[1]);
        }
    }
    return defaultValue;
}

function computeMarkupLocation(field) {
    var minX = 999999;
    var minY = 999999;
    $.each(field.segments, function(segment_idx, segment) {
        if (segment.segment_x < minX) {
            minX = segment.segment_x;
        }
        if (segment.segment_y < minY) {
            minY = segment.segment_y;
        }
    });
    return {
        x: minX + 5,
        y: minY + 2
    };
}

function drawMultilineText($canvas, properties){
    var strings = String(properties.text).split('\n');
    var currentY = properties.y;
    properties = $.extend({
        method: "drawText",
        lineSpacing: 0
    }, properties);
    $.each(strings, function(idx, string) {
        var lineProperties = $.extend(Object.create(properties), {
            text: string,
            y: currentY
        });
        var measurements = $canvas.measureText(lineProperties);
        $canvas.addLayer(lineProperties);
        currentY += properties.lineSpacing + measurements.height;
    });
}

function viewAsImage() {
    //Create a modal
    var $formImage = $('.formImage');
    var uriContent = $("canvas").getCanvasImage("jpeg", 1.0);
    $formImage.replaceWith("<img src='" + uriContent + "' ></img>");
}
$("canvas").hide();
$('.save-instructions').hide();

function createForm(form) {
    var $canvas = $("canvas").jCanvas();
    var $bar = $('.bar');
    var progress = 10;
    var numFields = form.fields.length;
    var default_font = "9pt Verdana, sans-serif";
    $bar.css('width', '10%');

    //////Draw canvas background:
    $canvas.attr('height', form.height + ' px');
    $canvas.attr('width', form.width + ' px');
    //Make bg white (rather than transparent)
    $canvas.addLayer({
        method: 'drawRect',
        fillStyle: "#fff",
        fromCenter: false,
        x: 0,
        y: 0,
        height: form.height,
        width: form.width
    });
    //Draw page border:
    $canvas.addLayer({
        method: 'drawRect',
        strokeStyle: "#000",
        strokeWidth: 1,
        fromCenter: false,
        x: 12, y: 12,
        width: (form.width - 24),
        height: (form.height - 24)
    });
    $canvas.addLayer({
        method: 'drawRect',
        strokeStyle: "#000",
        strokeWidth: 1,
        fromCenter: false,
        x: 8, y: 8,
        width: (form.width - 16),
        height: (form.height - 16)
    });
    //Draw form title:
    drawMultilineText($canvas, {
        x: form.width / 2,
        y: 50,
        fillStyle: "#000",
        align: "center",
        baseline: "middle",
        font: form.font || default_font,
        text: form.form_title || ''
    });
    //Draw page number
    drawMultilineText($canvas, {
        x: form.width / 2,
        y: (form.height - 30),
        fillStyle: "#000",
        align: "center",
        baseline: "middle",
        font: form.font || default_font,
        text: form.page_number || ''
    });
    
    ///////Draw form:
    $.each(form.fields.concat(form.markup ? form.markup : []), function(field_idx, field) {
        field = $.extend({}, form, field);
        progress += 90 / numFields;
        $bar.css('width', progress + '%');
        
        var markup_object = {
            fillStyle: "#000",
            opacity: 0.7,
            x: 0,
            y: 0,
            align: "left",
            baseline: "top",
            font: form.font || default_font,
            text: field.label || (field.name || '')
        };
        $.extend(markup_object, computeMarkupLocation(field));
        if ("markup_location" in field) {
            $.extend(markup_object, field.markup_location);
        }

        drawMultilineText($canvas, markup_object);
        
        $.each(field.segments, function(segment_idx, segment) {
            var classifier;
            segment = $.extend({}, field, segment);
            classifier = segment.classifier;
            $canvas.addLayer({
                method: 'drawRect',
                strokeStyle: "#000000",
                strokeWidth: 2,
                fromCenter: false,
                x: segment.segment_x,
                y: segment.segment_y,
                width: segment.segment_width,
                height: segment.segment_height
            });
            if ('items' in segment) {
                $.each(segment.items, function(item_idx, item) {
                    $canvas.addLayer({
                        method: classifier.training_data_uri === "bubbles" ? "drawEllipse" : "drawRect",
                        strokeStyle: "#55d",
                        strokeWidth: 1.6,
                        fromCenter: true,
                        name: "myBox",
                        group: "myBoxes",
                        x: segment.segment_x + item.item_x,
                        y: segment.segment_y + item.item_y,
                        width: classifier.classifier_width * 0.65,
                        height: classifier.classifier_height * 0.65
                    });
                    if ('label' in item) {
                        var itemLabelObj = {
                            fillStyle: "#000",
                            opacity: 0.7,
                            x: segment.segment_x + item.item_x - (0.75 * classifier.classifier_width),
                            y: segment.segment_y + item.item_y,
                            align: "right",
                            font: form.font || default_font,
                            text: item.label
                        };
                        drawMultilineText($canvas, itemLabelObj);
                    }
                });
            }
            else {

            }
        });

    });$canvas.drawLayers();
    if (progress >= 99) {
        window.setTimeout(function() {
            $bar.parent().hide();
            $('.save-instructions').show();
        }, 1000);
    }
    var fiducials = [{
        source: "fiducials/cs.jpg",
        x: 60,
        y: 55
    }, {
        source: "fiducials/villagereach.png",
        x: form.width - 140,
        y: (form.height - 40)
    }, {
        source: "fiducials/scan.png",
        x: 80,
        y: (form.height - 40)
    }, {
        source: "fiducials/change.jpg",
        x: form.width - 70,
        y: 50
    }];
    if ('fiducials' in form) {
        fiducials = form.fiducials;
    }
    
    var fiducialLoaded = (function() {
        var fiducialsLoaded = 0;
        return function(){
            console.log('fiducial loaded');
            fiducialsLoaded++;
            if (fiducialsLoaded === 4) {
                viewAsImage();
            }
        }
    })();
    $.each(fiducials, function(fiducial_idx, fiducial) {
        $canvas.drawImage($.extend({}, {
            x: 0,
            y: 0,
            load: fiducialLoaded,
            fromCenter: true //I think this has to be true if there is no height/width
        }, fiducial));
    });
    window.setTimeout(function() {
        //If the fiducials don't load in 10 seconds pretend they did.
        fiducialLoaded();
        fiducialLoaded();
        fiducialLoaded();
        fiducialLoaded();
    }, 10000);
}