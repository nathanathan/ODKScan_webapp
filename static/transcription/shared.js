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
function saveModified(callback) {
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
function modified(){
    $(this).addClass('modified');
    $('.save').attr("disabled", false).text('save');
}