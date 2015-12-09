(function() {

angular.module("app", ["ui.bootstrap", "ngAnimate", 
    "services", "navbar"])
    
.controller("ListController", ["$scope", "$http", "$interval", "Ratings", "Changes", 
    function ListController($scope, $http, $interval, Ratings, Changes) {
    $scope.mode = true; // set default mode true = watchlist.
    // convert Ratings to a list ordered alphabetically by name
    $scope.ratings = [];
    $scope.collapseList = [];
    Ratings.get().then(function(data) {
        for (k in data) {
            $scope.data = data;
            $scope.ratings.push(data[k]);    
        }
        $scope.ratings.sort(function(a,b) { return a.name.localeCompare(b.name); });

        // initialize collapseList
        var booleanArray = [];
        for (var i=0; i < $scope.ratings.length; i++) {
            booleanArray.push(true);
        }
        $scope.collapseList = booleanArray;
    });

    $scope.collapseChanged = function(index) {
        index = parseInt(index);
        console.log("collapse changed " + index);
        console.log(typeof index);
        
        var newList = $scope.collapseList.map(function(val, i) { 
            if (i===index) {
                return !val; // toggle the changed element
            } else {
                return true; // collapse all others
            };
        });

        $scope.collapseList = newList;
    };

    var updatePromise = $interval(function(){ Changes.post(); }, 2000);
    $scope.$on('$destroy', function() {
        console.log("update interval cancelled");
        $interval.cancel(updatePromise);
    });
}])
.directive("seriesItem", function() {
    return {
        restrict: "E",
        templateUrl: "/static/templates/series-item.html",
        scope: {
            mode: "=",
            seriesRating: "=",
            isCollapsed: "=",
            index: "@",
            onToggle: "&"
        },
        // transclude: true,
        controller: ["$scope", "$timeout", "Series", "Ratings", "Changes", "baseImgUrl", "convertDate", 
            function SeriesItemController($scope, $timeout, Series, Ratings, Changes, baseImgUrl, convertDate) {
            $scope.baseImgUrl = baseImgUrl;
            $scope.Changes = Changes;
            // $scope.isCollapsed = true; // set by parent
            $scope.seriesJson = {};

            var now = new Date(); // used to tell if an episode has aired
            $scope.hasAired = function(otherDate) {
                if(!otherDate) return false;
                return otherDate.getTime() < now.getTime();
            };

            Series.get($scope.seriesRating.id).then(function success(data){
                console.log()
                $scope.seriesJson = data;
                Ratings.initSeries(data);
                updateUnwatchedUnairedCount();
                // notify all children that ratings has been initialized
                $timeout(function() {
                    console.log("broadcasting ratings-ready");
                    $scope.$broadcast("ratings-ready");
                }, 1000);
            });

            $scope.unwatchedEpisodes = 0; // episodes aired not yet watched
            $scope.unairedEpisodes = 0; // episodes not yet aired
            var updateUnwatchedUnairedCount = function() {
                var unairedEpisodes = 0;
                var unwatchedEpisodes = 0;
                var seasons = $scope.seriesRating.seasons;
                for (var season in seasons) {
                    var episodes = seasons[season].episodes;
                    for (var episode in episodes) {
                        if(!episodes[episode].watched) {
                            var airedDate = $scope.seriesJson.seasons[season]
                                .episodes[episode].air_date;
                            if($scope.hasAired(airedDate)) {
                                unwatchedEpisodes++;
                            } else {
                                unairedEpisodes++;
                            };
                        };
                    }
                }
                $scope.unwatchedEpisodes = unwatchedEpisodes;
                $scope.unairedEpisodes = unairedEpisodes;
            }
            
            // event listeners
            $scope.checkboxChanged = function() {
                Changes.getSeries($scope.seriesJson.id).tracking = 
                    $scope.seriesRating.tracking;
            };

            $scope.ratingChanged = function() {
                Changes.getSeries($scope.seriesJson.id).rating = 
                    $scope.seriesRating.rating;
            }

            $scope.$on("episode-watched-changed", function() {
                updateUnwatchedUnairedCount();
            });
        }]
    }
})
.controller("SeasonItemController", ["$scope",
    function SeasonEntryController($scope) {
    $scope.seasonWatched = false;
    
    function getSeasonWatched() {
        var watched = true;
        for (var episode in $scope.seasonRating.episodes) {
            watched = watched && $scope.seasonRating.episodes[episode].watched;
        };
        $scope.seasonWatched = watched;
    }

    $scope.$on("ratings-ready", function() {
        console.log("season received ratings-ready");
        $scope.seasonRating = $scope.seriesRating.seasons[$scope.seasonNum];
        getSeasonWatched(); 
    });

    $scope.$on("episode-watched-changed", function() {
        getSeasonWatched();
    });

    $scope.checkboxChanged = function() {
        var episodes = $scope.seasonRating.episodes;
        for (var episodeNum in episodes) {
            var episode = episodes[episodeNum];
            // don't need to do anything if episode.watched will not change
            if (episode.watched === $scope.seasonWatched) continue;

            // don't marked unaired episodes watched
            if ($scope.hasAired($scope.seasonJson.episodes[episodeNum].air_date)) {
                episode.watched = $scope.seasonWatched;
                $scope.Changes.getEpisode(
                    $scope.seriesJson.id, 
                    $scope.seasonNum, 
                    episodeNum).watched = $scope.seasonWatched;
            }
        }
        // emit also notifies own scope, so seasonWatched will be updated
        $scope.$emit("episode-watched-changed");
    };
}])
.controller("EpisodeItemController", ["$scope", function EpisodeEntryController($scope) {
    $scope.episodeRating = undefined;
    $scope.episodeNotAired = !$scope.hasAired($scope.episodeJson.air_date);
    $scope.$on("ratings-ready", function() {
        console.log("episode received ratings-ready");
        $scope.episodeRating = $scope.seasonRating.episodes[$scope.episodeNum];
    });

    $scope.checkboxChanged = function() {
        $scope.Changes
            .getEpisode(
                $scope.seriesJson.id, 
                $scope.seasonNum, 
                $scope.episodeNum).watched = $scope.episodeRating.watched 

        $scope.$emit("episode-watched-changed");
    }

    $scope.ratingChanged = function() {
        $scope.Changes
            .getEpisode(
                $scope.seriesJson.id, 
                $scope.seasonNum, 
                $scope.episodeNum).rating = $scope.episodeRating.rating;
        if ($scope.episodeRating.rating != 0 && !$scope.episodeRating.watched) {
            // any non-zero rating will mark episode watched
            $scope.episodeRating.watched = true;
            $scope.checkboxChanged();
        }
    }

}])

})();