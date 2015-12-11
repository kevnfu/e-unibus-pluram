(function(){

angular.module("navbar", ["ngAnimate"])
.value("userName", $('meta[name=user-name]').attr('content'))

.filter("nospace", [function() {
    return function(s) {
        if (!angular.isString(s)) {
            return s;
        };
        return s.replace(/[\s]/g, "");
    };
}])

.directive("navBar", ["userName", function(userName) {
    return {
        restrict: "E",
        scope: {
            searchTerm: "=",
            submitCallback: "&onSubmit"
        },
        templateUrl: "/static/templates/navbar.html",
        link: function(scope) {
            scope.name = userName;
            scope.navbarCollapsed = true;
            scope.submit = function() {
                scope.submitCallback();
            }
        }
    };
}]);

})();