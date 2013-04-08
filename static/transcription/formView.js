function computeTextLocation(field) {
    var minX = 999999;
    var avgY = 0;
    $(field.segments).each(

    function(segment_idx) {
        var segment = this;
        if (segment.quad) {
            var quad = segment.quad;
            avgY += (quad[0][1] + quad[1][1] + quad[2][1] + quad[3][1]) / 4;
            if (quad[0][0] < minX) {
                minX = quad[0][0];
            }
        }
    });
    avgY /= field.segments.length;
    return {
        x: Math.abs(minX - 30),
        y: avgY
    };
}
function renderMarkedupForm(form){
    var formLocation = getParameter('formLocation', "");
    var selectedSegment = getParameter('segment');
    var formId = getParameter("formId");
    if(selectedSegment){
		var $doneBtn = $('<button class="btn btn-primary">Done</button>');
		$doneBtn.click(function(){
			window.close();
		});
		$('body').append($('<center>').append($doneBtn));
    }
    var $canvas = $("canvas").jCanvas();
    $(".main-image").attr('src', formLocation + "aligned.jpg");
    $(".main-image").load(function() {
        $canvas.attr('height', $(this).height());
        $canvas.attr('width', $(this).width());


            var $bar = $('.bar');
            var progress = 10;
            var numFields = form.fields.length;
            $bar.css('width', '10%');
            $(form.fields).each(

            function(field_idx) {
                var field = form.fields[field_idx];
                progress += 90 / numFields;
                $bar.css('width', progress + '%');
				
                if (selectedSegment) {
                    $(field.segments).each(
                
                    function(segment_idx) {
                        var segment = this;
                        if (segment.quad) {
                            var quad = segment.quad;
                            var isSelected = (selectedSegment == field.name + '_image_' + segment_idx);
                            if (isSelected) {
                                $canvas.addLayer({
                                    method: 'drawLine',
                                    strokeStyle: "#00ff09",
                                    strokeWidth: 4,
                                    x1: quad[0][0],
                                    y1: quad[0][1],
                                    x2: quad[1][0],
                                    y2: quad[1][1],
                                    x3: quad[2][0],
                                    y3: quad[2][1],
                                    x4: quad[3][0],
                                    y4: quad[3][1],
                                    closed: true,
                                    radius: 100,
                                    click: function() {}
                                });
                            }
                        }
                    });
                    return;
                }
				
                var textLocation, textLayerParams, textLayer;
                if(typeof field.markup_location === 'undefined'){
                    textLocation = computeTextLocation(field);
                } else {
                    textLocation = field.markup_location;
                }
                
                textLayerParams = {
                    name: "field_" + field_idx + "_text",
                    baseline: "top",
                    align: "left",
                    method: "drawText",
                    fillStyle: "#9cf",
                    strokeStyle: "#25a",
                    opacity: 0.7,
                    strokeWidth: 4,
                    font: "12pt Verdana, sans-serif",
                    text: field.transcription || field.value
                };
                textLayer = $canvas.addLayer($.extend(textLayerParams, textLocation));

                $(field.segments).each(

                function(segment_idx) {
                    var segment = this;
                    if (segment.quad) {
                        var quad = segment.quad;
                        var isSelected = (selectedSegment == field.name + '_image_' + segment_idx);
                        var strokeStyle = "#00ff09";
                        if(typeof field.transcription === 'undefined'){
                        	strokeStyle = isSelected ? "#fff200" : "#ffb700";
                        }
                        var createModal = function(){
                            //TODO: Do this with a template.
                            //currently it modifies the modal included in the HTML.
                            var $body = $('.modal-body');
                            $body.empty();
                            $(field.segments).each(function(segment_idx) {
                                $body.append(
                                $('<img>').attr('src', formLocation + "segments/" + field.name + '_image_' + segment_idx + '.jpg'));
                            });
		                    $('.modal-header').find('h3').text(field.label || field.name);
                            var $control;
                            if (field.type.indexOf('select') >= 0) {
                                var $select = $('<select>').addClass('transcription').change(modified);
                                if (field.type === 'select') {
                                    $select.attr("multiple", "multiple");
                                }
                                $select.append($('<option value>'));
                                var items = field.items || field.segments[0].items;
                                $.each(items, function(item_idx, item) {
                                    var $option = $('<option>');
                                    $option.text(item.label || item.value);
                                    if("transcription" in item){
                                        $option.val(item.transcription);
                                    } else {
                                        $option.val(item.value);
                                    }
                                    $select.append($option);
                                });
                                $control = $select;
                            
                            } else {
                                $control = $('<input>').addClass('transcription').keydown(modified);
                            }
                            $control.attr('name', formId + '-' + field.name);
                            $control.val($("canvas").getLayer("field_" + field_idx + "_text").text);
                            $body.append($('<div>').append($control));
                            //$body.find('select').chosen();
                            
                            var $saveBtn = $('<button>').addClass("btn").addClass("btn-primary");
                            $saveBtn.attr("type", "submit").text('set').addClass('setBtn');
                            $saveBtn.click(function() {
                                $saveBtn.attr("disabled", true).text('setting...');
                                saveModified(function() {
                                    $canvas.getLayer("field_" + field_idx + "_text").text = $control.val();
                                    var layers = $canvas.getLayerGroup("field_" + field_idx);
                                    $(layers).each(function(layer_idx) {
                                        layers[layer_idx].strokeStyle = "#00ff09";
                                    });
                                    $canvas.click();
                                    $('#myModal').modal('hide');
                                });
                            });
                            $(".setBtn").replaceWith($saveBtn);
                            $('#myModal').modal('show');
                            $control.focus();
                        };
                        $canvas.addLayer({
                        	group: "field_" + field_idx,
                            method: 'drawLine',
                            strokeStyle: strokeStyle,
                            strokeWidth: 4,
                            x1: quad[0][0],
                            y1: quad[0][1],
                            x2: quad[1][0],
                            y2: quad[1][1],
                            x3: quad[2][0],
                            y3: quad[2][1],
                            x4: quad[3][0],
                            y4: quad[3][1],
                            closed: true,
                            radius: 100,

                            click: function(layer) {
                                var segmentQuad = $(this);
                                var oldclick = layer.click;
                                //disable click during animation.
                                layer.click = function() {};
                                segmentQuad.animateLayer(layer, {
                                    strokeStyle: "#00ff09"
                                }, 10, function() {
                                    //re-enable click.
                                    layer.click = oldclick;
                                    createModal();
                                });

                            }
                        });
                        $(segment.items).each(

                        function(item_idx) {
                            var item = this;
                            $canvas.addLayer({
                                method: "drawRect",
                                strokeStyle: item.classification ? "#00ff44" : "#ff00ff",
                                strokeWidth: 3,
                                opacity: .4,
                                fromCenter: true,
                                x: item.absolute_location[0],
                                y: item.absolute_location[1],
                                width: 5,
                                height: 5
                            });
                        });
                    }
                });
            });
            if (progress > 99) {
                window.setTimeout(function() {
                    $bar.parent().remove();
                }, 1000);
            }
            $canvas.click();


    });

    window.onbeforeunload = function() {
        if ($('.modified').length > 0) {
            return "If you navigate away from this page you will loose unsaved changes.";
        }
    };

}
