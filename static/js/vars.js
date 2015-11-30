var imgUrl = $('meta[name=img-url]').attr('content');

var seriesItem = function(series_json) {

};

var getSeries = function(id) {
    $.getJSON('http://localhost:8080/series/' + id.toString())  
        .done(function(data) {
            console.log(data.name);
        })
        .fail(function() {
            console.log('fail');
        });
};