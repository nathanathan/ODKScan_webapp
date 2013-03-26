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
    window.onbeforeunload = function(){ 
	  if ($('.modified').length > 0) {
	    return "If you navigate away from this page you will loose unsaved changes.";
	  }
	};
    $('input').keydown(modified);
    $('select').change(modified);
	//$('select').chosen();
	$('.segment').click(function(e){
		//e.preventDefault();
		var win = window.open($(this).attr('href'), "Field View", 'width=900,scrollbars=yes');
		//Logging:
	    var params = {
	    	url : String(window.location),
	    	activity : "table-view-click-segment",
	    	formImage : $(this).attr('formid'),
	    	fieldName : $(this).attr('fieldname'),
	    	segment : $(this).find('img').attr('src')//TODO
	    };
	    $.ajax({
		  url: "/log/",
		  type: "POST",
		  data: params,
		  cache: false
		}).fail(function( xhr ) {
			$('body').replaceWith($('<pre>').text(xhr.responseText));
		});
	});
});