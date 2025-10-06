# anubis/principal/urls.py

from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = "principal"

urlpatterns = [
    # ==============================================================================
    # ROTAS GERAIS E DE NAVEGAÇÃO PRINCIPAL
    # ==============================================================================
    path("", views.home, name="home"),
    path("perfil/", views.perfil, name="perfil"), 
    path("perfil/editar/", views.editar_perfil, name="editar_perfil"), # Página para editar o perfil
    path("usuario/<str:user_id>/", views.perfil_usuario, name="perfil_usuario"), # Perfil público de outros usuários
    path("busca/", views.pagina_de_busca, name="pagina_de_busca"),
    path("criar-clube/", views.criar_clube, name="criar_clube"),

    # ==============================================================================
    # ROTAS DE CLUBES (VISUALIZAÇÃO E INTERAÇÃO BÁSICA)
    # ==============================================================================
    path('clube/<int:clube_id>/', views.detalhes_clube, name='detalhes_clube'),
    path('clube/<int:clube_id>/entrar/', views.entrar_clube, name='entrar_clube'),
    path('clube/<int:clube_id>/sair/', views.sair_clube, name='sair_clube'),
    path('clube/<int:clube_id>/solicitar-entrada/', views.solicitar_entrada_privado, name='solicitar_entrada_privado'),


    # ==============================================================================
    # ROTAS DA ESTANTE DO CLUBE
    # ==============================================================================
    path('estante/<int:clube_id>/', views.estante, name='estante'),
    path('estante/<int:clube_id>/lidos/', views.lidos_view, name='lidos'), 
    path('estante/<int:clube_id>/abandonados/', views.abandonados_view, name='abandonados'),
    path('estante/<int:clube_id>/queremos/', views.queremos_ler_view, name='queremos_ler'),  
    path('clube/<int:clube_id>/admin/alterar-status-leitura/<int:leitura_id>/', views.alterar_status_livro, name='alterar_status_livro'),

    # ==============================================================================
    # ROTAS DE AÇÕES DIRETAS DO USUÁRIO
    # ==============================================================================
    path('clube/<int:clube_id>/votacao/<int:votacao_id>/votar/', views.registrar_voto, name='registrar_voto'),
    path('clube/<int:clube_id>/livro/<int:livro_id>/iniciar_leitura/', views.iniciar_leitura, name='iniciar_leitura'),
    path('estante_pessoal/<int:estante_pessoal_id>/atualizar_progresso/', views.atualizar_progresso, name='atualizar_progresso'),
    path('leitura/<int:leitura_id>/avaliar/', views.registrar_nota_clube, name='registrar_nota_clube'),
    # ==============================================================================
    # ROTAS DE ADMINISTRAÇÃO DO CLUBE 
    # ==============================================================================
    path('clube/<int:clube_id>/admin/editar/', views.editar_clube, name='editar_clube'),
    path('clube/<int:clube_id>/admin/excluir/', views.excluir_clube, name='excluir_clube'),
    path('clube/<int:clube_id>/transferir-admin/', views.transferir_admin_clube, name='transferir_admin_clube'),
    path('clube/<int:clube_id>/admin/definir-leitura-atual/', views.definir_leitura_atual_clube, name='definir_leitura_atual_clube'),
    path('clube/<int:clube_id>/admin/adicionar-livro-estante/', views.adicionar_livro_estante_clube, name='adicionar_livro_estante_clube'),
    
    # Gerenciamento de Votações
    path('clube/<int:clube_id>/admin/criar-votacao/', views.criar_votacao_clube, name='criar_votacao_clube'),
    path('clube/<int:clube_id>/votacao/<int:votacao_id>/editar/', views.editar_votacao, name='editar_votacao'),
    path('clube/<int:clube_id>/votacao/<int:votacao_id>/fechar/', views.fechar_votacao, name='fechar_votacao'),

    # Gerenciamento de Reuniões
    path('clube/<int:clube_id>/criar_reuniao/', views.criar_reuniao, name='criar_reuniao'),
    path('clube/<int:clube_id>/reuniao/<int:reuniao_id>/editar/', views.editar_reuniao, name='editar_reuniao'),
    
    # ==============================================================================
    # ROTAS DE ADMINISTRAÇÃO DE MEMBROS
    # ==============================================================================
    path('clube/<int:clube_id>/admin/gerenciar-membros/', views.gerenciar_membros, name='gerenciar_membros'),
    path('clube/<int:clube_id>/admin/convidar/', views.convidar_membro, name='convidar_membro'),
    path('clube/<int:clube_id>/membro/<int:membro_id>/aprovar/', views.aprovar_membro, name='aprovar_membro'),
    path('clube/<int:clube_id>/membro/<int:membro_id>/rejeitar/', views.rejeitar_membro, name='rejeitar_membro'),
    path('clube/<int:clube_id>/membro/<int:membro_id>/promover/', views.promover_membro, name='promover_membro'),
    path('clube/<int:clube_id>/membro/<int:membro_id>/rebaixar/', views.rebaixar_membro, name='rebaixar_membro'),
    path('clube/<int:clube_id>/membro/<int:membro_id>/remover/', views.remover_membro, name='remover_membro'),
    path('clube/<int:clube_id>/membro/<int:membro_id>/banir/', views.banir_membro, name='banir_membro'),
    path('clube/<int:clube_id>/membro/<int:membro_id>/desbanir/', views.desbanir_membro, name='desbanir_membro'),

    # ==============================================================================
    # ROTAS DE API (PARA CHAMADAS JAVASCRIPT)
    # ==============================================================================
    path('api/buscar-livros/', views.buscar_livros_api, name='buscar_livros_api'),
    path('clube/<int:clube_id>/admin/adicionar-livro-api/', views.adicionar_livro_api_para_estante, name='adicionar_livro_api_para_estante'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)