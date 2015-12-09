(function() {

angular.module("services", [])

.constant("baseImgUrl", $('meta[name=img-url]').attr('content'))
.constant("now", (new Date()).getTime())
.service("Ratings", ["$http", Ratings])
.service("Changes", ["$http", Changes])
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
        }
    };
}]);

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
    this.changes = new Changes($http);
};
Ratings.prototype = {
    get: function() {
        var ctx = this;
        return this.$http.get("/account/rating", {cache:true})
            .then(function success(result) {
                console.log("loaded ratings");
                ctx.json = result.data;
                return ctx.json;
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

}

function Changes($http) {
    this.$http = $http;
    this.json = {};
};
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
};


})();