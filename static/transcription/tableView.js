jQuery(function($) {
    //Does hiding and showing of columns
	$('.icon-eye-open').hide();
    $('th').click(function(){
    	if(!$(this).hasClass('hidden')){
    		$(this).addClass('hidden');
	    	$('.'+$(this).attr('id')).children().hide(); //.children(':not(select)').hide();
	    	$(this).children('.label').hide();
	    	$(this).children('.icon-eye-open').show();
    	}
    	else{
    		$(this).removeClass('hidden');
    		$('.'+$(this).attr('id')).children().show();//.children(':not(select)').show();
	    	$(this).children('.label').show();
	    	$(this).children('.icon-eye-open').hide();
    	}
    });
    //Saving behavior
    $('.save').attr("disabled", true).text('saved');
    window.onbeforeunload = function() {
        if ($('.modified').length > 0) {
            return "If you navigate away from this page you will loose unsaved changes.";
        }
    };
    $('input').keydown(modified);
    $('select').change(modified);

	$('.segment').click(function(e){
		window.open($(this).attr('href'), "Field View", 'width=900,scrollbars=yes');
	});
    function saveModified(callback){
        $.ajax({
            type: 'POST',
            url: "/save_transcription/",
            data: $('.modified').serialize(),
            success: function() {
                console.log('saved');
                $('.modified').removeClass('modified');
                callback();
            }
        }).fail(function(xhr) {
            $('body').replaceWith($('<pre>').text(xhr.responseText));
        });
    }
    function modified(e){
        $(this).addClass('modified');
        $('.save').attr("disabled", false).text('save');
    }

	$("form").submit(function(e) {
        e.preventDefault();
        console.log('submit');
        $('.save').attr("disabled", true).text('saving...');
        saveModified(function(){$('.save').attr("disabled", true).text('saved');});
	});
    
});