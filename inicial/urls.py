from django.urls import path
from . import views

app_name = "inicial"

urlpatterns = [
    path("", views.inicial, name="inicial"),
    path("cadastro/", views.cadastrar_usuario, name= "cadastro"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout_usuario, name="logout"),
    path('busca/', views.inicial_busca_view, name='inicial_busca'),

    path('validar_email/<str:token>/', views.validate_email_view, name='validar_email'),
    path('recuperar_senha/', views.request_password_reset, name='recuperar_senha'),
    path('redefinir_senha/<str:token>/', views.reset_password_view, name='redefinir_senha'),
    path('termos-de-uso/', views.termos_de_uso, name='termos_de_uso'),
]