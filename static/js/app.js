(function() {

angular.module("app", ["ui.bootstrap", "ngAnimate", "services", "navbar"])
    
.controller("ListController", ["$scope", "$interval", "$timeout", "Series", "Ratings", "Changes", 
    function ListController($scope, $interval, $timeout, Series, Ratings, Changes) {
    $scope.mode = true; // set default mode true = watchlist.
    $scope.searchTerm = ""; // search term in navbar
    $scope.searchQuery = undefined; // search term sent to <search-results/>
    $scope.seriesListVisible = true;
    $scope.alerts = [];

    $scope.closeAlert = function(index) {
        $scope.alerts.splice(index, 1);
    }

    // convert Ratings to a list ordered alphabetically by name
    $scope.ratings = [];
    $scope.collapseMap = {};

    // get ratings from server
    Ratings.get().then(function(data) {
        $scope.data = data;
        // convert ratings data (an object) into an array
        for (k in data) {
            $scope.ratings.push(data[k]);
        }
        // alphabetically
        sortRatingsAlpha()

        // initialize collapseMap
        for (var i in $scope.ratings) {
            var rating = $scope.ratings[i];
            $scope.collapseMap[rating.id] = true;
        }
    });

    function sortRatingsAlpha() {
        $scope.ratings.sort(function(a,b) { return a.name.localeCompare(b.name); });
    }

    function escapeRegExp(str) {
      return str.replace(/[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g, "\\$&");
    }
    $scope.matchSearch = function(name) {
        return name.toLowerCase().match($scope.searchTermRegex);
    }
    $scope.$watch("searchTerm", function() {
        $scope.searchTermRegex = new RegExp(escapeRegExp($scope.searchTerm.toLowerCase()));
    });

    $scope.collapseChanged = function(seriesId) {
        console.log("collapse changed " + seriesId);
        for (var id in $scope.collapseMap) {
            id = parseInt(id);
            if (id===seriesId) {
                 $scope.collapseMap[id] = !$scope.collapseMap[id];
            } else {
                $scope.collapseMap[id] = true;
            }
        }
    };

    var updatePromise = $interval(function(){ Changes.post(); }, 2000);
    $scope.$on('$destroy', function() {
        console.log("update interval cancelled");
        $interval.cancel(updatePromise);
    });

    $scope.endOfList = function() {
        console.log("at the end");
    }
    
    // navbar stuff
    $scope.searchResultsVisible = false;
    $scope.navbarSubmit = function() {
        if ($scope.searchTerm === "") {
            return;
        }
        $scope.searchQuery = angular.copy($scope.searchTerm);
        $scope.searchResultsVisible = true;
        $scope.seriesListVisible = false;
    }

    $scope.addSeries = function(data) {
        console.log(data && ("add series:" + data.id));
        if (!data) {
            $scope.searchResultsVisible = false;
            $scope.seriesListVisible = true;
            $scope.searchTerm = "";
            return;
        } else if (data.id in Ratings.json) {
            $scope.alerts.push({
                type:"warning", 
                msg:"Already added.", 
                time:2000
            })
        } else {
            Changes.getSeries(data.id).name = data.name;
            $scope.alerts.push({
                type:"success",
                msg:"Series added.",
                time:2000
            })
            // tell server to load series
            Series.post(data.id).then(function success() {
                var newSeries = Ratings.addSeries(data.id, data.name);
                $scope.ratings.push(newSeries);
                sortRatingsAlpha();
                $scope.collapseMap[data.id] = true;
            });
        }

        $timeout(function() {
            $scope.searchResultsVisible = false;
            $scope.seriesListVisible = true;
            $scope.searchTerm = "";
        }, 500);
    }
}])
.directive("seriesItem", function() {
    return {
        restrict: "E",
        templateUrl: "/static/templates/series-item.html",
        scope: {
            mode: "=",
            seriesRating: "=",
            isCollapsed: "=",
            onToggle: "&"
        },
        controller: ["$scope", "$uibModal", "Series", "Ratings", "Changes", "posterPath", "convertDate", 
            function SeriesItemController($scope, $uibModal, Series, Ratings, Changes, posterPath, convertDate) {
            $scope.basePosterUrl = posterPath(0);
            $scope.Changes = Changes;

            // $scope.isCollapsed = true; // set by parent
            $scope.seriesJson = {};

            var now = new Date(); // used to tell if an episode has aired
            $scope.hasAired = function(otherDate) {
                if(!otherDate) return false;
                return otherDate.getTime() < now.getTime();
            };

            $scope.seenAll = function() {
                return ($scope.unwatchedEpisodes===0) && ($scope.unairedEpisodes===0);
            }

            Series.get($scope.seriesRating.id).then(function success(data){
                console.log()
                $scope.seriesJson = data;
                Ratings.initSeries(data);
                updateUnwatchedUnairedCount();
            });

            $scope.unwatchedEpisodes = true; // seen all aired episodes
            $scope.unairedEpisodes = 0; // episodes not yet aired
            var updateUnwatchedUnairedCount = function() {
                var unairedEpisodes = 0;
                var unwatchedEpisodes = 0;
                var seasonsJson = $scope.seriesJson.seasons;
                for (var seasonNum in seasonsJson) {
                    var episodesJson = seasonsJson[seasonNum].episodes;
                    for (var episodeNum in episodesJson) {
                        var episodeJson = episodesJson[episodeNum];
                        var episodeRating = $scope.seriesRating
                            .seasons[seasonNum].episodes[episodeNum]
                        if(!episodeRating.watched) {
                            if($scope.hasAired(episodeJson.air_date)) {
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
    // set initial state
    $scope.seasonRating = $scope.seriesRating.seasons[$scope.seasonNum];
    getSeasonWatched(); 

    function getSeasonWatched() {
        var watched = true;
        for (var episode in $scope.seasonJson.episodes) {
            watched = watched && $scope.seasonRating.episodes[episode].watched;
        };
        $scope.seasonWatched = watched;
    }

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
            var episodeJson = $scope.seasonJson.episodes[episodeNum];
            if ($scope.hasAired(episodeJson && episodeJson.air_date)) {
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
    $scope.episodeRating = $scope.seasonRating.episodes[$scope.episodeNum];
    // $scope.$on("ratings-ready", function() {
    //     console.log("episode received ratings-ready");
    //     $scope.episodeRating = $scope.seasonRating.episodes[$scope.episodeNum];
    // });

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
.directive("onBecomeVisible", ["$parse", "$window", function($parse, $window) {
    // usage: on-become-visible="callback()"
    // callback() is called when the element comes into view,
    // that is, before the scroll or resize, it was not visible.
    // once it becomes visible, callback is called.
    // it will not call again until it leaves and then returns into view.
    return {
        restrict: "A",
        link: function(scope, elem, attr) {
            var callback = $parse(attr.onBecomeVisible);
            
            function isElementInViewport (el) {
                //special bonus for those using jQuery
                if (el instanceof jQuery) {
                    el = el[0];
                }

                var rect = el.getBoundingClientRect();

                return (
                    rect.top >= 0 &&
                    rect.left >= 0 &&
                    rect.bottom <= $(window).height() &&
                    rect.right <= $(window).width()
                );
            };

            // var oldVisible = isElementInViewport(elem);
            // angular.element($window).on('DOMContentLoaded load resize scroll', function() {
            //     var newVisible = isElementInViewport(elem);
            //     if (oldVisible===false && newVisible === true) {
            //         callback(scope);
            //     }
            //     oldVisible = newVisible;
            // });
            angular.element($window).on('DOMContentLoaded load resize scroll', function() {
                if (isElementInViewport(elem)) {
                    callback(scope);
                }
            });
        }
    }
}])
.directive("searchResults", ["searchTv", "posterPath", function(searchTv, posterPath) {
    return {
        restrict: "E",
        scope: {
            query: "=",
            onSelectSeries: "&"
        },
        templateUrl: "/static/templates/search-tv.html",
        link: function(scope, elem, attr) {
            scope.mouseover=false;
            scope.basePosterUrl = posterPath(2);
            scope.active = true;

            function updateResults(page) {
                searchTv.get(scope.query, page)
                    .then(function(data) {
                        if(!data.results){
                            console.log("no results");
                            return;
                        }

                        scope.totalPages = data.total_pages;
                        console.log("page " + page + 
                            " out of " + scope.totalPages);

                        data = data.results;
                        // filter out results w/o poster
                        var i = data.length;
                        while (i--) {
                            if (data[i].poster_path==null) {
                                data.splice(i,1);
                            }
                        }
                        if (data===null) {
                            return;
                        }
                        if (scope.page===1) {
                            scope.results = data;
                        } else {
                            $.merge(scope.results, data);
                        }})
            }

            scope.$watch("query", function() {
                scope.results = [];
                scope.page = 0;
                scope.active = true;
                updateResults(++scope.page);
                if (scope.page < scope.totalPages) {
                    updateResults(++scope.page);
                }
                if (scope.page < scope.totalPages) {
                    updateResults(++scope.page);
                }
            })

            scope.endOfList = function() {
                if (!scope.active) return;
                if (scope.page < scope.totalPages) {
                    updateResults(++scope.page);
                }
                if (scope.page < scope.totalPages) {
                    updateResults(++scope.page);
                }
                if (scope.page < scope.totalPages) {
                    updateResults(++scope.page);
                }
            }

            scope.selected = function(id, name) {
                id = parseInt(id);
                // only show clicked result
                for (var i in scope.results) {
                    if (scope.results[i].id === id) {
                        scope.results = [scope.results[i]];
                        break;
                    }
                }
                scope.onSelectSeries()(scope.results[0]);
                scope.active = false;
            }

            scope.cancel = function() {
                scope.onSelectSeries()();
                scope.active = false;
            }
        },
    };
}])
.directive("mouseoverImg", [function() {
    return {
        restrict: "E",
        scope: {
            src: "@"
        },
        template: '<img src="src" ng->',
        link: function(scope, elem, attr) {

        }
    }
}])

})();