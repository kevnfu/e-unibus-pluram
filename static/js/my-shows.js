// (function() {

// Global vars
var baseImgUrl = $('meta[name=img-url]').attr('content'),
    ratings,
    seriesList;

// function baseImgUrl() {
//     return $('meta[name=img-url]').attr('content');
// };

// enum for page mode
var mode = {
    watchlist: "watchlist",
    all: "all",
    sync: false,
    async: true
};

function pageMode(mode) {
    var currentMode = $('#pagemode').find('.active:first').data('value');
    if (mode===currentMode) {
        return true;
    } else {
        return false;
    }
};

// Models

function Changes() {
    this.json = {};
}
Changes.prototype = {
    getSeries: function(series) {
        return seriesChanges = this.json[series] 
            || (this.json[series] = {
                // 'name':seriesList.seriesItem(series).name(), 
                'seasons':{}});
    },
    getSeason: function(series, season) {
        var seriesChanges = this.getSeries(series);
        return seriesChanges.seasons[season] 
            || (seriesChanges.seasons[season] = {'episodes':{}});
    },
    getEpisode: function(series, season, episode) {
        var seasonChanges = this.getSeason(series, season);
        return seasonChanges.episodes[episode] 
            || (seasonChanges.episodes[episode] = {});
    },
    post: function(mode) {
        if($.isEmptyObject(this.json)) { 
            console.log('No changes to sync');
            return; 
        };

        jString = JSON.stringify(this.json);
        console.log('syncing changes: ' + jString);
        $.ajax({
            url: '/account/rating',
            type: 'POST',
            async: mode,
            success: function(){console.log("posted changes")},
            data: jString,
            contentType: "application/json",
            dataType: 'json'});

        this.json = {};
    }
}

function Ratings(json) {
    this.json = json;
    this.ordered = [];
    for (var key in json) {
        this.ordered.push(json[key])
    };
    this.changes = new Changes();
};
Ratings.prototype = {
    episodeWatched: function(series, season, episode) {
        var watched = false;
        var season = this.json[series].seasons[season];
        if (season===undefined || season.episodes[episode]===undefined) {
            watched = false;
        } else {
            var episode = season.episodes[episode];
            watched = episode.watched;
        };
        return watched;
    },
    setEpisodeWatched: function(series, season, episode, watched) {
        this.changes.getEpisode(series, season, episode)['watched'] = watched;
    },
    setTracking: function(series, tracking) {
        // series id and boolean tracking
        this.changes.getSeries(series)['tracking'] = tracking;
    },
    tracking: function(series) {
        return this.json[series].tracking;
    },
    watchedSeason: function(series, season) {
        var seasonRating = this.json[series].seasons[season],
            season = seriesList.seriesItem(series, season);

        for(ep in season) {
            seasonRating[ep].watched = true;
        };
    },
    sortAlpha: function() {
        this.ordered.sort(function(a,b) {
            return a.name.localeCompare(b.name);
        });
        return this.ordered;
    }
};

// wrappers around json data
function Series(json) {
    this.json = json;
    this.seasons = {};
    for (num in json.seasons) {
        this.seasons[num] = new Season(this, json.seasons[num]);
    };
};
Series.prototype = {
    id: function() { return this.json.id; },
    name: function() { return this.json.name; },
    airDate: function() { return this.json.air_date; },
    poster: function() { return this.json.poster_path; },
    season: function(num) { return this.json.seasons[num]; }
};

function Season(parent, json) {
    this.parent = parent;
    this.json = json;
    this.episodes = {};
    for (num in json.episodes) {
        this.episodes[num] = new Episode(this, json.episodes[num]);
    };
};
Season.prototype = {
    number: function() { return this.json.season_number; },
    name: function() { return "Season " + this.number() },
    airDate: function() { return this.json.air_date; },
    episode: function(num) { return this.episodes[num]; }
};

function Episode(parent, json) {
    this.parent = parent;
    this.json = json;
};
Episode.prototype = {
    number: function() { return this.json.episode_number; },
    name: function() { return this.json.name; },
    airDate: function() { return this.json.air_date; },
};

// views
function SeriesList() {
    // map from series id to seriesitem
    this.map = {};
};
SeriesList.prototype = {
    append: function(item) {
        item.appendTo('#series-list');
    },
    seriesItem: function(series) {
        return this.map[series];
    },
    addSeries: function(series) {
        var ctx = this;

        $.getJSON('/series/' + series)  
            .done(function(data) {
                var newItem = (new SeriesItem(data));
                ctx.map[data.id] = newItem;
                ctx.append(newItem.element);
            })
            .fail(function() {
                console.log('loadSeries fail for ' + series);
            });
    },
};

 function SeriesItem(json) {
    this.json = json;
    var newItem = $(buildSeriesItem(json.name, 
        baseImgUrl + json.poster_path, json.id));
    this.element = newItem;
    
    // set up element

    // click listener for changing glyphicon
    newItem.find('.float-left').click(function() {
        $(this).toggleClass('active, inactive');
    });

    // set tracking state of series-item
    var trackingSeries = ratings.tracking(json.id);
    var series_checkbox = newItem.find('.series-check:first');
    series_checkbox.prop('checked', trackingSeries);
    if (!trackingSeries && pageMode(mode.watchlist)) {
        newItem.hide();
    };

    // click listener for series tracking
    series_checkbox.click(function() {
        var checked = $(this).prop('checked');
        ratings.setTracking(json.id, checked);
        if (!checked && pageMode(mode.watchlist)) {
            $(this).closest('.series-item').hide();
        };
    });

    // build table
    var tbody = newItem.find('tbody');
    for (var i = 1; i <= json.number_of_seasons; i++) {
        var season = json.seasons[i];
        var seasonEntry = $(buildSeasonEntry(season));

        // clicking watched for season will set children episodes
        seasonEntry.find('input[type=checkbox]:first').click(function() {
            var checked = $(this).prop('checked');
            console.log("marking season watched " + checked);
            if (pageMode(mode.watchlist)) {
                $(this).closest(".series-entry").hide();
            };

            //click all children
            $(this).closest('.series-entry').nextUntil('.success').each(function() {
                var episodeCheckbox = $(this).find('input[type=checkbox]:first');
                if (episodeCheckbox.prop('checked') !== checked) {
                    episodeCheckbox.click();
                };
            });
        });

        tbody.append(seasonEntry);
        var watchedSeason = true;
        for (var j = 1; j <= season.number_of_episodes; j++) {
            var episode = season.episodes[j];
            var entry = $(buildEpisodeEntry(json.id, episode));
            var watchedEpisode = ratings.episodeWatched(json.id, i, j);
            var checkbox = entry.find('input[type=checkbox]:first');

            checkbox.prop('checked', watchedEpisode);
            entry.appendTo(tbody);

            // every episode must be watched for season to be watched
            watchedSeason &= watchedEpisode;

            if (watchedEpisode && pageMode(mode.watchlist)) {
                checkbox.closest('.series-entry').hide();
            };

            checkbox.click((function(i,j) {
                return function() {
                    var checked = $(this).prop('checked');
                    ratings.setEpisodeWatched(json.id, i, j, checked);
                    if (checked && pageMode(mode.watchlist)) {
                        $(this).closest('.series-entry').hide();
                    };
                };
            })(i,j));
        };

        // update season watched  checkbox
        seasonEntry.find('input[type=checkbox]:first').prop('checked', watchedSeason);
        if(watchedSeason && pageMode(mode.watchlist)) {
            seasonEntry.hide();
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
    season: function(i) {
        return this.json.seasons[i];
    },
};

function loadData() {
    seriesList = new SeriesList();

    // get rating data
    $.getJSON('/account/rating')
        .done(function(data){
            // initialize ratings object
            ratings = new Ratings(data);
            ratings.sortAlpha();

            for(var i=0; i<ratings.ordered.length; i++) {
                var id = ratings.ordered[i].id
                console.log('loading: ' + id);
                seriesList.addSeries(id);
            };
        })
        .fail(function(){
            console.log('loadRatings fail');
        });
};

function attachListeners() {
    // listeners for the all shows and watched options
    $('#all-btn').click(function() {
        $('.series-entry').each(function(){
                $(this).show();
            });

            $('.series-item').each(function(){
                var checked = $(this).find('.series-check:first').prop('checked');
                $(this).show();
            });
    });

    $('#watchlist-btn').click(function() {
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
};

// document events
$(document).ready(function(){
    loadData();
    attachListeners();
    var date = new Date();
});

window.onbeforeunload = function() {
    ratings.changes.post(mode.sync);
};

// sync w/ server on intervals
(function sync(){
    if (ratings){
        ratings.changes.post(mode.async);
    };
    setTimeout(sync, 10000);
})();


// })();


