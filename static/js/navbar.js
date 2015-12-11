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
            searchTerm: "="
        },
        templateUrl: "/static/templates/navbar.html",
        link: function(scope) {
            scope.name = userName;
            scope.navbarCollapsed = true;
        },
        // controller: ["$scope", "userName", function($scope, userName) {
        //     $scope.name = userName;
        //     $scope.text = "";
        //     $scope.navbarCollapsed = true;
        //     $scope.getText = function() {
        //         return $scope.text;
        //     };
        // }]
    };
}]);

})();