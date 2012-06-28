//This does some magic so django CSRF tokens work.
jQuery(document).ajaxSend(function(event, xhr, settings) {
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    function sameOrigin(url) {
        // url could be relative or scheme relative or absolute
        var host = document.location.host; // host + port
        var protocol = document.location.protocol;
        var sr_origin = '//' + host;
        var origin = protocol + sr_origin;
        // Allow absolute or scheme relative URLs to same origin
        return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
            (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
            // or any other URL that isn't scheme relative or absolute i.e relative.
            !(/^(\/\/|http:|https:).*/.test(url));
    }
    function safeMethod(method) {
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    if (!safeMethod(settings.type) && sameOrigin(settings.url)) {
        xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
    }
});

function saveModified(callback){
	var groupedParams = {};
	var modArray = $('.modified').serializeArray();
	for(i in modArray){
		var mod = modArray[i];
		if(mod.name in groupedParams){
			groupedParams[mod.name] += ', ' + mod.value;
		} else {
			groupedParams[mod.name] = mod.value;
		}
	}
	console.log($.param(groupedParams));
	$.post("/save_transcription/", $.param(groupedParams),
		function(){
			console.log('saved');
			$('.modified').removeClass('modified');
			callback();
		});
}
function modified(){
    $(this).addClass('modified');
	$('.save').attr("disabled", false).text('save');
}
jQuery(function($) {
	$("form").submit(function(e) {
	    	e.preventDefault();
	    	console.log('submit');
	    	$('.save').attr("disabled", true).text('saving...');
	    	saveModified(function(){$('.save').attr("disabled", true).text('saved');});
	});
});