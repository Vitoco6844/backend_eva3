from django.urls import path

from . import administration as views


app_name = "administration"

urlpatterns = [
    path("", views.index, name="index"),
    path("usuarios/", views.users, name="users"),
    path("usuarios/nuevo/", views.create, name="create"),
    path("usuarios/<int:pk>/editar/", views.edit, name="edit"),
]
