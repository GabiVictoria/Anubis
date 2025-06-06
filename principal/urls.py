from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


app_name = "principal"

urlpatterns = [
    path("", views.home, name="home"),
    path("criar-clube/", views.criar_clube, name="criar_clube"),
    path("busca/", views.pagina_de_busca, name="pagina_de_busca"),
    path('clube/<int:clube_id>/', views.detalhes_clube, name='detalhes_clube'),

    path('clube/<int:clube_id>/sair/', views.sair_clube, name='sair_clube'),
    path('clube/<int:clube_id>/entrar/', views.entrar_clube, name='entrar_clube'),
    path('clube/<int:clube_id>/votacao/<int:votacao_id>/votar/', views.registrar_voto, name='registrar_voto'),
    path('clube/<int:clube_id>/admin/editar/', views.editar_clube_info, name='editar_clube_info'),
    path('clube/<int:clube_id>/admin/adicionar-livro-estante/', views.adicionar_livro_estante_clube, name='adicionar_livro_estante_clube'),
    path('clube/<int:clube_id>/admin/definir-leitura-atual/', views.definir_leitura_atual_clube, name='definir_leitura_atual_clube'),
    path('clube/<int:clube_id>/admin/criar-votacao/', views.criar_votacao_clube, name='criar_votacao_clube'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)