// Global vars
var baseImgUrl = $('meta[name=img-url]').attr('content');
var ratings;
var seriesList;
// classes
var Ratings = function(json) {
    this.json = json;
};
Ratings.prototype = {
    constructor: Ratings,
    getSeries: function(id) {
        return this.json[id];
    },
    getSeason: function(id, s) {
        var season = this.json[id].seasons[s];
    },
    postWatched: function() {

    },
    tracking: function(series) {
        return this.json[series].tracking;
    },
    watchedEpisode: function(series, season, episode) {
        var watched = false;
        var season = this.json[series].seasons[season];
        if (season===undefined || season.episodes[episode]===undefined) {
            watched = false;
        } else {
            var episode = season.episodes[episode];
            watched = episode.watched;
        }
        return watched;
    },
};

var SeriesList = function() {
    this.list = [];
};
SeriesList.prototype = {
    constructor: SeriesList,
    append: function(item) {
        item.appendTo('#series-list');
    },
    addSeries: function(series) {
        var ctx = this;

        $.getJSON('/series/' + series)  
            .done(function(data) {
                var newItem = (new SeriesItem(data));
                ctx.list.push(newItem);
                ctx.append(newItem.element);
            })
            .fail(function() {
                console.log('loadSeries fail for ' + series);
            });
    },
};

var SeriesItem = function(json) {
    this.json = json;
    var newItem = $(buildSeriesItem(json.name, json.poster_path, json.id));
    this.element = newItem;
    
    // set up element

    // click listener for changing glyphicon
    newItem.find('.float-left').click(function() {
        $(this).toggleClass('active, inactive');
    });

    // set checked state
    var series_checkbox = newItem.find('.series-check:first');
    series_checkbox.prop('checked', ratings.tracking(json.id));

    // click listener for series-checkbox
    series_checkbox.click(function() {
        $.post('/account/rating/tracking', {
            series_id:json.id,
            value:$(this).prop('checked')})
            .done(function(){
                console.log(series_checkbox.prop('checked'));
            })
            .fail(function(){
                console.log('series track fail');
            });
    });

    // build table
    var tbody = newItem.find('tbody');
    for (var i = 1; i <= json.number_of_seasons; i++) {
        var season = json.seasons[i];
        tbody.append(buildSeasonEntry(season));
        for (var j = 1; j <= season.number_of_episodes; j++) {
            var episode = season.episodes[j];
            var entry = $(buildEpisodeEntry(json.id, episode));
            entry.appendTo(tbody)

            var checkbox = entry.find('input[type=checkbox]:first')
            checkbox.click((function(i,j,c) {
                return function(){
                    $.post('/account/rating/watched', {
                        series_id:json.id,
                        season_num:i,
                        episode_num:j,
                        value:c.prop('checked')})
                        .done(function() {
                            console.log(c.prop('checked'));
                        })
                        .fail(function() {
                            console.log('watch post failed');
                        });
                };
            })(i,j,checkbox));
        };
    };

};
SeriesItem.prototype = {
    constructor: SeriesItem,
    name: function() {
        return this.json.name;
    },
    poster_path: function() {
        return this.json.poster_path;
    },
};

var loadData = function() {
    seriesList = new SeriesList();

    // get rating data
    $.getJSON('/account/rating')
        .done(function(data){
            // initialize ratings object
            ratings = new Ratings(data);
            for(var id in data) {
                console.log('loading: ' + id);
                seriesList.addSeries(id);
            };
        })
        .fail(function(){
            console.log('loadRatings fail');
        });
};

var attachListeners = function() {
    // listeners for the all shows and watched options

    $('#displayAll').click(function(){
        $('.series-entry').each(function(){
            $(this).show();
        });

        $('.series-item').each(function(){
            var checked = $(this).find('.series-check:first').prop('checked');
            $(this).show();
        });
    });

    $('#displayWatchlist').click(function(){
        $('.series-entry').each(function(){
            var checkbox = $(this).find('.entry-check:first');
            if (checkbox.prop('checked')) {
                $(this).hide();
            };
        });

        $('.series-item').each(function(){
            var checked = $(this).find('.series-check:first').prop('checked');
            console.log(checked);
            if (!checked) {
                $(this).hide();
            };
        });
    });
}

$(document).ready(function(){
    // loadSeries(56570);
    loadData();
    attachListeners();
});