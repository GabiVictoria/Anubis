from django.urls import path
from . import views

app_name = "inicial"

urlpatterns = [
    path("", views.inicial, name="inicial"),
    path("cadastro/", views.cadastrar_usuario, name= "cadastro"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout_usuario, name="logout"),
    path('busca/', views.inicial_busca_view, name='inicial_busca'),
]