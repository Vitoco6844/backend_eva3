from django.urls import path
from .views import register

urlpatterns = [path("registro/", register, name="customer-register")]
