from django.urls import include, path

urlpatterns = [path("api/", include("web.eva4_api"))]
