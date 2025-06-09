# anubis/principal/urls.py

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

    # Ações do usuário no clube
    path('clube/<int:clube_id>/sair/', views.sair_clube, name='sair_clube'),
    path('clube/<int:clube_id>/entrar/', views.entrar_clube, name='entrar_clube'),
    path('clube/<int:clube_id>/votacao/<int:votacao_id>/votar/', views.registrar_voto, name='registrar_voto'),

    # Rotas de admin do clube
    path('clube/<int:clube_id>/admin/editar/', views.editar_clube, name='editar_clube'),
      path('clube/<int:clube_id>/admin/excluir/', views.excluir_clube, name='excluir_clube'),
    path('clube/<int:clube_id>/admin/definir-leitura-atual/', views.definir_leitura_atual_clube, name='definir_leitura_atual_clube'),
    path('clube/<int:clube_id>/admin/criar-votacao/', views.criar_votacao_clube, name='criar_votacao_clube'),

    # --- ROTAS NOVAS E MODIFICADAS PARA API DE LIVROS ---
    # 1. Endpoint que o JavaScript vai chamar para buscar livros
    path('api/buscar-livros/', views.buscar_livros_api, name='buscar_livros_api'),
    # 2. Página para o admin iniciar o processo de adição de livro (agora uma página de busca)
    path('clube/<int:clube_id>/admin/adicionar-livro-estante/', views.adicionar_livro_estante_clube, name='adicionar_livro_estante_clube'),
    # 3. Endpoint que recebe o POST para salvar o livro selecionado no banco de dados
    path('clube/<int:clube_id>/admin/adicionar-livro-api/', views.adicionar_livro_api_para_estante, name='adicionar_livro_api_para_estante'),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)