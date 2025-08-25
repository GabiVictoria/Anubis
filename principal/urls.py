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
    path("perfil/", views.perfil, name="perfil"), 
    

     # Rotas da estante aninhadas sob 'estante/'
    path('estante/<int:clube_id>/', views.estante, name='estante'),
    path('estante/<int:clube_id>/lidos/', views.lidos_view, name='lidos'), 
    path('estante/<int:clube_id>/abandonados/', views.abandonados_view, name='abandonados'),
    path('estante/<int:clube_id>/proximo/', views.proximo_livro_view, name='proximo_livro'), 
    path('estante/<int:clube_id>/queremos/', views.queremos_ler_view, name='queremos_ler'), 
    path('estante/<int:clube_id>/releitura/', views.releitura_view, name='releitura'), 
   




    # Ações do usuário no clube
    path('clube/<int:clube_id>/sair/', views.sair_clube, name='sair_clube'),
    path('clube/<int:clube_id>/entrar/', views.entrar_clube, name='entrar_clube'),
    path('clube/<int:clube_id>/votacao/<int:votacao_id>/votar/', views.registrar_voto, name='registrar_voto'),
    path('estante_pessoal/<int:estante_pessoal_id>/atualizar_progresso/', views.atualizar_progresso, name='atualizar_progresso'),
    path('clube/<int:clube_id>/livro/<int:livro_id>/iniciar_leitura/', views.iniciar_leitura, name='iniciar_leitura'),

    # Rotas de admin do clube
    path('clube/<int:clube_id>/admin/editar/', views.editar_clube, name='editar_clube'),
    path('clube/<int:clube_id>/admin/excluir/', views.excluir_clube, name='excluir_clube'),
    path('clube/<int:clube_id>/transferir-admin/', views.transferir_admin_clube, name='transferir_admin_clube'),
    path('clube/<int:clube_id>/admin/definir-leitura-atual/', views.definir_leitura_atual_clube, name='definir_leitura_atual_clube'),
    path('clube/<int:clube_id>/admin/criar-votacao/', views.criar_votacao_clube, name='criar_votacao_clube'),
    path('clube/<int:clube_id>/criar_reuniao/', views.criar_reuniao, name='criar_reuniao'),
    path('reuniao/<int:reuniao_id>/editar/', views.editar_reuniao, name='editar_reuniao'),
    path('clube/<int:clube_id>/votacao/<int:votacao_id>/editar/', views.editar_votacao, name='editar_votacao'),
    path('votacao/<int:votacao_id>/fechar/', views.fechar_votacao, name='fechar_votacao'),


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