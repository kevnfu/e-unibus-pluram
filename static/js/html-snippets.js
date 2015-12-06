const HTMLTableEntry = [
    '<tr class="series-entry %classes%">',
      '<td>%title%</td>',
      '<td>5</td>',
      '<td>%airdate%</td>',
      '<td><input class="entry-check" type="checkbox"></td>',
    '</tr>'
].join('\n');

function buildSeasonEntry(json) {
    var str = HTMLTableEntry
        .replace("%title%", 'Season ' + json.season_number)
        .replace('%airdate%', json.airdate)
        .replace('%classes%', 'success');

    return str;
}

function buildEpisodeEntry(series_id, json) {
    var se = ['S', json.season_number, 
            'E', json.episode_number, ' ', json.name].join('');
    var str = HTMLTableEntry
        .replace('%title%', se)
        .replace('%airdate%', json.air_date)
        .replace('%classes%', '');

    return str;
};

const HTMLSeriesItem = [
  '<article class="series-item">',
    '<div id="%id%" class="row">',
      '<div class="col-xs-12">',
        '<a class="active toggler float-left" data-toggle="collapse" data-target="#t-%id%">',
          '<span class="glyphicon glyphicon-triangle-right"></span>',
          '<span class="glyphicon glyphicon-triangle-bottom"></span>',
          '<img class="image-responsive series-image" src="%imgurl%" alt="Poster">',
        '</a>',
        '<div><h4><a href="#">%title%</a></h4></div>',
        '<div><a href="#">Rating</a></div>',
        '<div><label>currently tracking <input class="series-check" type="checkbox" name="keywords"></label></div>',
      '</div>',
    '</div>',
    '<div id="t-%id%" class="collapse">',
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
        '</tbody>',
      '</table>',
    '</div>',
  '</article>'
].join('\n');

var buildSeriesItem = function(name, poster, id) {
    var str = HTMLSeriesItem.replace('%title%', name)
        .replace('%imgurl%', baseImgUrl + poster)
        .replace(/%id%/g, id);

    return str;
};