from django.urls import path
from . import views

app_name = "inicial"

urlpatterns = [
    path("", views.inicial),
    path("cadastro/", views.cadastrar_usuario, name= "cadastro"),
    path("login/", views.login, name="login")
]