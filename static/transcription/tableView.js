jQuery(function($) {
    //Does hiding and showing of columns
	$('.icon-eye-open').hide();
    $('th').click(function(){
        if(!$(this).hasClass('hidden')){
            $(this).addClass('hidden');
            $('.'+$(this).attr('id')).children().hide();
            $(this).children('.label').hide();
            $(this).children('.icon-eye-open').show();
        }
        else{
            $(this).removeClass('hidden');
            $('.'+$(this).attr('id')).children().show();
            $(this).children('.label').show();
            $(this).children('.icon-eye-open').hide();
        }
    });
    //Saving behavior
    $('.save').attr("disabled", true).text('saved');

    $('input').keydown(modified);
    $('select').change(modified);

	$('.segment').click(function(e){
		window.open($(this).attr('href'), "Field View", 'width=900,scrollbars=yes');
	});
	$("form").submit(function(e) {
        e.preventDefault();
        console.log('submit');
        $('.save').attr("disabled", true).text('saving...');
        saveModified(function(){$('.save').attr("disabled", true).text('saved');});
	});
    
    window.onbeforeunload = function() {
        if ($('.modified').length > 0) {
            return "If you navigate away from this page you will loose unsaved changes.";
        }
    };
});