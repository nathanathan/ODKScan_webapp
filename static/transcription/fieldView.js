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

jQuery(function($) {
    //Saving behavior
    $('.save').attr("disabled", true).text('saved');
    $("form").submit(function(e) {
        e.preventDefault();
        $('.save').text('saving...');
        console.log($('.modified').serialize());
        $.post("/save_transcription/", $('.modified').serialize(), function() {
            $('.save').attr("disabled", true).text('saved');
            $('.modified').removeClass('modified');
        });
    });
    var formLocation = getParameter('formLocation', "");
    var jsonOutputUrl = formLocation + "output.json";
    $.getJSON(jsonOutputUrl, function(form) {
        var fieldObj = form.fields[getParameter('fieldIdx')];
        $('.modal-header').find('h3').text(fieldObj.name);
        var $body = $('.modal-body');
        $(fieldObj.segments).each(
        function(segment_idx) {
            $body.append(
            $('<img>').attr('src', formLocation + "segments/" + fieldObj.name + '_image_' + segment_idx + '.jpg'));
        });
        console.log(fieldObj);
        var $control = $('<form>').addClass;
        $control.append($('<label>').text(fieldObj.label));
        if(fieldObj.type === 'select'){
            var $select = $('<select>').addClass('transcription');
            $(fieldObj.items).each(function(item_idx){//We might have a problem here
                $select.append($('<option>').text(fieldObj.items[item_idx].label));
            });
            $control.append($select);
        } else {
            $control.append($('<input>').addClass('transcription'));
        }
        
        $body.append($control);
    });

    //Saving behavior
    $('.save').attr("disabled", true).text('saved');
    $("form").submit(function(e) {
        e.preventDefault();
        console.log(window.opener.document);//getParameter('fieldIdx')
        window.opener.document.getElementById("updater").value = "HI";
    	$('.save').text('saving...');
    	console.log($('.modified').serialize());
        /*
    	$.post("/save_transcription/", $('.modified').serialize(),
    		function(){
    			$('.save').attr("disabled", true).text('saved');
    			$('.modified').removeClass('modified');
    		});
        */
        //window.close();
    });
    $('input').keydown(function(){
		$(this).addClass('modified');
		$('.save').attr("disabled", false).text('save');
    });
    $('select').onchange(function(){
    	$(this).addClass('modified');
		$('.save').attr("disabled", false).text('save');
    });

});