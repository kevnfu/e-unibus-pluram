(function() {

angular.module("services", [])
.constant("now", (new Date()).getTime())
.constant("tmdbKey", $('meta[name=tmdb-key]').attr('content'))
.service("Ratings", ["$http", Ratings])
.service("Changes", ["$http", "$timeout", Changes])
.factory("posterPath", function() {
    var posterPaths = $('meta[name=poster-paths]').attr('content').split(" ");
    return function(size) {
        return posterPaths[size];
    }
})
.factory("convertDate", [function() {
    return function(dateStr) {
        // format is YYYY-MM-DD
        if (!dateStr) return undefined;
        dateStr = dateStr.split("-");
        return new Date(dateStr[0], dateStr[1]-1, dateStr[2]);
    };
}])
.factory("Series", ["$http", "convertDate", function seriesFactory($http, convertDate) {
    return {
        get: function(id) {
            return $http.get("/series/" + id, {cache: true})
                .then(function success(result) {
                    var seriesJson = result.data;
                    console.log("loaded series: " + seriesJson.id);
                    return parseAiredDates(seriesJson, convertDate);
                });
        },
        post: function(id) {
            return $http.post("/series/" + id, {})
                .then(function success() {
                    console.log("posted series: " + id);
                });
        }
    };
}])
.factory("searchTv", ["$http", "tmdbKey", function($http, tmdbKey) {
    var searchStr = 'http://api.themoviedb.org/3/search/tv?api_key=' 
        + tmdbKey +"&query=";
    return {
        get: function(title, page) {
            page = page || 1;
            return $http.get(
                searchStr + encodeURI(title) + "&page=" + page)
                .then(function success(result) {
                    return result.data;
                });
        }
    };
}])

function parseAiredDates(seriesJson, convertDate) {
    //convert all aired dates to dates

    for(var seasonNum in seriesJson.seasons) {
        var seasonJson = seriesJson.seasons[seasonNum];
        for (var episodeNum in seasonJson.episodes) {
            var episodeJson = seasonJson.episodes[episodeNum];
            var airedDate = convertDate(episodeJson.air_date);
            episodeJson.air_date = airedDate;
        }
    }

    return seriesJson;
}


// stores initial ratings
function Ratings($http) {
    this.$http = $http;
    this.json = {};
    this.list = [];
    this.changes = new Changes($http);
    this.the = /^the /i;
};
Ratings.prototype = {
    get: function() {
        var ctx = this;
        return this.$http.get("/account/rating", {cache:true})
            .then(function success(result) {
                console.log("loaded ratings");
                ctx.json = result.data;
                for (k in ctx.json) {
                    ctx.list.push(ctx.json[k]);
                }
                return ctx.list;
            });
    },
    sortAlpha : function() {
        // ignores leading "the"
        this.list.sort(function(a,b) { 
            a = a.name.replace(this.the, "");
            b = b.name.replace(this.the, "");
            return a.localeCompare(b); 
        });
    },
    initSeries: function(json) {
        // since new episodes could've been added to series, need to
        // instantiate every season/episode rating
        seriesRating = this.json[json.id];
        for (var season in json.seasons) {   
            if (!(season in seriesRating.seasons)){
                seriesRating.seasons[season] = {rating:0, episodes:{}};
            }
            for (var episode in json.seasons[season].episodes) {
                if (!(episode in seriesRating.seasons[season].episodes)) {
                   seriesRating.seasons[season].episodes[episode] = {watched:false, rating:0};
                }
            }
        }
    },
    addSeries: function(id, name) {
        var newSeries = {'id':id, 'name':name, 
            'tracking':true, 'rating':0, 'seasons': {}};
        this.json[id] = newSeries;
        this.list.push(newSeries);
        return newSeries;
    },
    getSeries: function(id) {
        return this.json[id];
    },
    escapeRegExp: function(str) {
        return str.replace(/[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g, "\\$&");
    },
    search: function(query) {
        // given a query, returns a rating whose name matches query
        // matches the beginning of words.
        // if no rating is found, returns undefined.
        if (!query) return;

        query = new RegExp("\\b" + this.escapeRegExp(query), "gi");
        for (rating of this.list) {
            if(rating.name.match(query)) {
                return rating;
                break;
            }
        }
    }

}

function Changes($http, $timeout) {
    this.$http = $http;
    this.$timeout = $timeout;
    this.json = {};
    this.promise = undefined;
};
Changes.prototype = {
    getSeries: function(series) {
        this.notify();
        return seriesChanges = this.json[series] 
            || (this.json[series] = {
                // 'name':seriesList.seriesItem(series).name(), 
                'seasons':{}});
    },
    getSeason: function(series, season) {
        this.notify();
        var seriesChanges = this.getSeries(series);
        return seriesChanges.seasons[season] 
            || (seriesChanges.seasons[season] = {'episodes':{}});
    },
    getEpisode: function(series, season, episode) {
        this.notify();
        var seasonChanges = this.getSeason(series, season);
        return seasonChanges.episodes[episode] 
            || (seasonChanges.episodes[episode] = {});
    },
    post: function(sync) {
        sync = (sync===undefined) ? "async" : sync;

        if($.isEmptyObject(this.json)) { 
            console.log('No changes to sync');
            return; 
        };

        var copy = this.json;
        this.json={};
        console.log('syncing changes: ' + JSON.stringify(copy));

        var url = "/account/rating";
        var success = function(){ console.log("synced!")}
        if (sync==="async") {
            this.$http.post(url, copy)
                .then(success)
        } else {
            $.ajax({
                type: "POST",
                url: url,
                data: JSON.stringify(copy),
                dataType: "json",
                async: false,
                success: success
            });
        };
    },
    notify: function() {
        // tells changes that changes have been made, it will wait 2s
        // to see if there's new data, then it will send.
        if (this.promise) {
            this.$timeout.cancel(this.promise);
        };
        var ctx = this;
        this.promise = this.$timeout(function() {
            ctx.post();
        }, 2000);
    }
};


})();