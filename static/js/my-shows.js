var baseImgUrl = $('meta[name=img-url]').attr('content');
var ratings;

var HTMLTableEntry = [
    '<tr class="%classes%">',
      '<td>%title%</td>',
      '<td>5</td>',
      '<td>%airdate%</td>',
      '<td><input type="checkbox" %checked%></td>',
    '</tr>'
].join('\n');

var buildEpisodeEntry = function(json) {
    var str = HTMLTableEntry
        .replace('%title%', ['S', json.season_number, 
            'E', json.episode_number, ' ', json.name].join(''))
        .replace('%airdate%', json.air_date)
        .replace('%classes%', '');
    if (true) {
        str = str.replace('%checked%', 'checked');
    } else {
        str = str.replace('%checked%', '');
    }
    return str;
};

var buildSeasonEntry = function(json) {
    var str = HTMLTableEntry
        .replace("%title%", 'Season ' + json.season_number)
        .replace('%airdate%', json.air_date)
        .replace('%classes%', 'success');
    if (true) {
        str = str.replace('%checked%', 'checked');
    } else {
        str = str.replace('%checked%', '');
    }
    return str;
}

var HTMLSeriesItem = [
    '<div class="row series-item">',
      '<div class="col-xs-12">',
        '<a class="active toggler" href="#" data-toggle="collapse" data-target="#%target%">',
          '<span class="glyphicon btn-lg glyphicon-triangle-right float-left"></span>',
          '<span class="glyphicon btn-lg glyphicon-triangle-bottom float-left"></span>',
          '<img class="image-responsive series-image" src="%imgurl%" alt="Poster">',
          '<div>',
            '<a href="#">%title%</a>',
          '</div>',
          '<div>',
          '<a href="#">Rating</a>',
          '</div>',
        '</a>',
      '</div>',
    '</div>',
    '<div id="%target%" class="collapse">',
      '<table class="table table-hover">',
        '<thead>',
          '<tr>',
            '<th>Title</th>',
            '<th>Rating</th>',
            '<th>Airdate</th>',
            '<th>Watched</th>',
          '</tr>',
        '</thead>',
        '<tbody>',
          '%entries%',
        '</tbody>',
      '</table>',
    '</div>'
].join('\n');

var buildSeriesItem = function(json) {
    var seasons = json.seasons;
    var entries = "";
    for (i = 1; i <= json.number_of_seasons; i++) {
        var season = seasons[i];
        entries += buildSeasonEntry(season);
        for (j = 1; j <= season.number_of_episodes; j++) {
            entries += buildEpisodeEntry(season.episodes[j]);
        };
    };
    var str = HTMLSeriesItem.replace('%title%', json.name)
        .replace('%entries%', entries)
        .replace('%imgurl%', baseImgUrl + json.poster_path)
        .replace(/%target%/g, json.id);

    return str;
};

var addSeriesItem = function(id) {
    $('#series-list').append(buildSeriesItem(json));
    $('#series-list').last().click(function() {
          $(this).toggleClass('active, inactive');
    });
};


var loadSeries = function(id) {
    $.getJSON('http://localhost:8080/series/' + id.toString())  
        .done(function(data) {
            addSeriesItem(data);
        })
        .fail(function() {
            console.log('fail');
        });
};


$(document).ready(function(){
    loadSeries(56570);
});