(function() {
angular.module("directives", [])

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
}]);

})()