angular.module("navbar", [])
.value("userName", $('meta[name=user-name]').attr('content'))

.filter("nospace", [function() {
    return function(s) {
        if (!angular.isString(s)) {
            return s;
        };
        return s.replace(/[\s]/g, "");
    };
}])

.directive("navBar", function() {
    return {
        restrict: "E",
        templateUrl: "/static/templates/navbar.html",
        controller: ["$scope", "userName", function($scope, userName) {
            $scope.name = userName;
            $scope.text = "";
            $scope.getText = function() {
                return $scope.text;
            };
        }]
    };
});

