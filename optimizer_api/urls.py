from django.urls import path
from .views import optimize_route_json, optimize_route_html

urlpatterns = [
    path(
        "<str:address1>/<str:address2>",
        optimize_route_json,
        name="route-optimizer-json",
    ),
    path(
        "map/<str:address1>/<str:address2>",
        optimize_route_html,
        name="route-optimizer-html",
    ),
]
