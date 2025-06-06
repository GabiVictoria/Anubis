from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponseForbidden
from django.contrib import messages
from django.utils import timezone
from .decorators import login_obrigatorio, admin_clube_obrigatorio
from inicial.models import Clube, ClubeMembro, LeituraClube,Livro,Votacao, VotoUsuario, Mensagem, Usuario
from django.db import IntegrityError

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db.models import Q
from .forms import ClubeEditForm, AdicionarLivroEstanteForm, DefinirLeituraAtualForm, CriarVotacaoForm
import os
# Create your views here.





@login_obrigatorio
def home(request: HttpRequest):
    usuario_atual = request.usuario_logado_obj
    query = request.GET.get('q', None) # Captura o parâmetro de busca, default para None

    # Buscar os clubes dos quais o usuário é membro
    clubes_do_usuario_qs = usuario_atual.clubes_participados.all()

    # Se houver uma query de busca, filtre os clubes
    if query:
        # Você pode expandir isso para buscar em descrições, livros, etc.
        clubes_do_usuario_qs = clubes_do_usuario_qs.filter(nome__icontains=query)
    
    clubes_do_usuario_qs = clubes_do_usuario_qs.order_by('nome')


    clubes_info_list = []
    for clube in clubes_do_usuario_qs:
        clube_info = {
            'id': clube.id,
            'nome': clube.nome,
            'descricao': clube.descricao, 
            # Você pode adicionar a URL da capa aqui se o campo capa_clube estiver preenchido
            'capa_clube_url': clube.capa_clube.url if clube.capa_clube else None,
            # Usando o novo campo data_criacao do modelo Clube
            'data_criacao': clube.data_criacao, 
            'membros_count': clube.membros.count(),
            'fundador_nome': "(a definir)", # Default
            'leitura_atual_nome': None # Default
            # Outros campos que você removeu do template não precisam ser adicionados aqui
            # a menos que você queira usá-los para outra coisa.
        }

        # Encontrar o fundador (primeiro administrador pela data de inscrição)
        admin_membro = ClubeMembro.objects.filter(clube=clube, cargo=ClubeMembro.Cargo.ADMIN).order_by('data_inscricao').first()
        if admin_membro:
            clube_info['fundador_nome'] = admin_membro.usuario.nome
            # Se você não tiver data_criacao no modelo Clube e quiser usar a data de inscrição do admin como 'desde':
            # if not clube.data_criacao: # Apenas se data_criacao do clube não existir
            #     clube_info['data_fundacao_estimada'] = admin_membro.data_inscricao

        # Encontrar a leitura atual do clube
        leitura_atual = LeituraClube.objects.filter(clube=clube, status=LeituraClube.StatusClube.LENDO_ATUALMENTE).select_related('livro').first()
        if leitura_atual and leitura_atual.livro:
            clube_info['leitura_atual_nome'] = leitura_atual.livro.nome
        
        clubes_info_list.append(clube_info)

    contexto = {
        "nome_usuario": usuario_atual.nome,
        "usuario_logado": True,
        "clubes_do_usuario": clubes_info_list,
        "search_query": query, # Passa o termo de busca de volta para repopular o campo
    }
    return render(request, 'principal/home.html', contexto)

@login_obrigatorio
def criar_clube(request: HttpRequest):
    # Contexto para repopular o formulário em caso de erro GET ou POST
    context_form_data = {
        'opcoes_privacidade': Clube.Privacidade.choices,
        'opcoes_limite_membros': Clube.LIMITE_MEMBROS_OPCOES,
    }

    if request.method == "POST":
        nome_clube = request.POST.get('nome_clube', '').strip()
        descricao_clube = request.POST.get('descricao_clube', '').strip()
        privacidade_clube_selecionada = request.POST.get('privacidade_clube')
        limite_membros_str_selecionado = request.POST.get('limite_membros')
        
        capa_clube_file = request.FILES.get('capa_clube') # Upload personalizado
        capa_recomendada_path_relativo = request.POST.get('capa_recomendada_selecionada')

        # Atualiza o contexto com os dados submetidos para repopulação em caso de erro
        context_form_data.update({
            'nome_clube': nome_clube,
            'descricao_clube': descricao_clube,
            'privacidade_selecionada': privacidade_clube_selecionada,
            'limite_selecionado': limite_membros_str_selecionado,
            # Não repopulamos 'capa_recomendada_selecionada' intencionalmente aqui
            # nem o 'capa_clube_file' por segurança e complexidade.
        })

        if not nome_clube or not descricao_clube:
            messages.error(request, "O nome e a descrição do clube são obrigatórios.")
            return render(request, 'principal/criar_clube.html', context_form_data)
        
        if not limite_membros_str_selecionado:
            messages.error(request, "O limite de membros é obrigatório.")
            return render(request, 'principal/criar_clube.html', context_form_data)

        try:
            limite_membros_int = int(limite_membros_str_selecionado)
        except ValueError:
            messages.error(request, "Valor inválido para limite de membros.")
            return render(request, 'principal/criar_clube.html', context_form_data)

        if privacidade_clube_selecionada not in [choice[0] for choice in Clube.Privacidade.choices]:
            messages.error(request, "Opção de privacidade inválida.")
            return render(request, 'principal/criar_clube.html', context_form_data)

        if Clube.objects.filter(nome__iexact=nome_clube).exists():
            messages.error(request, f"Já existe um clube com o nome '{nome_clube}'. Por favor, escolha outro nome.")
            return render(request, 'principal/criar_clube.html', context_form_data)

        usuario_criador = request.usuario_logado_obj

        try:
            novo_clube = Clube(
                nome=nome_clube,
                descricao=descricao_clube,
                privacidade=privacidade_clube_selecionada,
                limite_membros=limite_membros_int
            )

            # Lógica para capa: upload tem prioridade
            if capa_clube_file:
                novo_clube.capa_clube = capa_clube_file
            elif capa_recomendada_path_relativo:
                # Encontrar o caminho absoluto da imagem estática recomendada
                # Certifique-se que 'capa_recomendada_path_relativo' é algo como 'img/nome_da_imagem.jpg'
                caminho_absoluto_estatico = finders.find(capa_recomendada_path_relativo)
                
                if caminho_absoluto_estatico and os.path.exists(caminho_absoluto_estatico):
                    with open(caminho_absoluto_estatico, 'rb') as f:
                        django_file = ContentFile(f.read(), name=os.path.basename(capa_recomendada_path_relativo))
                        novo_clube.capa_clube = django_file
                else:
                    messages.warning(request, f"Imagem recomendada '{capa_recomendada_path_relativo}' não encontrada ou inválida. Clube será criado sem capa ou com a capa upada, se houver.")
            
            novo_clube.save() # Salva o clube para obter um ID e para que o ImageField processe o arquivo

            ClubeMembro.objects.create(
                usuario=usuario_criador,
                clube=novo_clube,
                cargo=ClubeMembro.Cargo.ADMIN
            )

            messages.success(request, f"Clube '{novo_clube.nome}' criado com sucesso!")
            return redirect('principal:home')

        # except IntegrityError: # IntegrityError já está no seu código original da view
        #     messages.error(request, "Ocorreu um erro de integridade ao tentar criar o clube. Verifique os dados.")
        #     return render(request, 'principal/criar_clube.html', context_form_data)
        except Exception as e: # Captura outras exceções de forma mais genérica
            messages.error(request, f"Ocorreu um erro inesperado ao criar o clube: {e}")
            return render(request, 'principal/criar_clube.html', context_form_data)
        
    # Se for método GET (página carregando pela primeira vez)
    return render(request, 'principal/criar_clube.html', context_form_data)

@login_obrigatorio
def pagina_de_busca(request: HttpRequest):
    query = request.GET.get('q', '').strip()
    resultados_finais = [] # Lista para armazenar os dicionários formatados para o template

    if query:
        # 1. Buscar clubes pelo nome
        clubes_por_nome = Clube.objects.filter(nome__icontains=query)

        # 2. Buscar clubes com base nos livros (LENDO ou PRÓXIMO)
        # Encontra os LeituraClube que correspondem ao nome do livro e ao status desejado
        leituras_com_livro_buscado = LeituraClube.objects.filter(
            Q(livro__nome__icontains=query) &
            (Q(status=LeituraClube.StatusClube.LENDO_ATUALMENTE) | Q(status=LeituraClube.StatusClube.PROXIMO))
        ).select_related('clube', 'livro') # select_related para otimizar

        # Coleta os clubes dessas leituras, evitando duplicatas se um clube aparecer em ambas as buscas
        clubes_encontrados_ids = set() # Para rastrear IDs de clubes já adicionados

        # Processa clubes encontrados por nome
        for clube in clubes_por_nome:
            if clube.id not in clubes_encontrados_ids:
                clubes_encontrados_ids.add(clube.id)
                # Monta o dicionário de informações para o template
                admin_membro = ClubeMembro.objects.filter(clube=clube, cargo=ClubeMembro.Cargo.ADMIN).order_by('data_inscricao').first()
                leitura_atual_obj = LeituraClube.objects.filter(clube=clube, status=LeituraClube.StatusClube.LENDO_ATUALMENTE).select_related('livro').first()
                
                resultados_finais.append({
                    'id': clube.id,
                    'nome': clube.nome,
                    'descricao': clube.descricao,
                    'capa_url': clube.capa_clube.url if clube.capa_clube else staticfiles_storage.url('img/default_club_placeholder.png'), # Imagem padrão
                    'fundador_nome': admin_membro.usuario.nome if admin_membro else "N/D",
                    'data_fundacao_formatada': clube.data_criacao.strftime("%B %Y") if clube.data_criacao else "N/D",
                    'membros_count': clube.membros.count(),
                    'leitura_atual_nome': leitura_atual_obj.livro.nome if leitura_atual_obj and leitura_atual_obj.livro else "Nenhuma leitura atual",
                    'match_reason': f"Nome do clube corresponde a '{query}'"
                })

        # Processa clubes encontrados por livros
        for leitura in leituras_com_livro_buscado:
            clube = leitura.clube
            if clube.id not in clubes_encontrados_ids: # Se ainda não foi adicionado pela busca por nome
                clubes_encontrados_ids.add(clube.id)
                admin_membro = ClubeMembro.objects.filter(clube=clube, cargo=ClubeMembro.Cargo.ADMIN).order_by('data_inscricao').first()
                # A leitura atual já é a 'leitura' se status LENDO, ou podemos buscar explicitamente
                leitura_atual_obj = LeituraClube.objects.filter(clube=clube, status=LeituraClube.StatusClube.LENDO_ATUALMENTE).select_related('livro').first()

                resultados_finais.append({
                    'id': clube.id,
                    'nome': clube.nome,
                    'descricao': clube.descricao,
                    'capa_url': clube.capa_clube.url if clube.capa_clube else staticfiles_storage.url('img/default_club_placeholder.png'),
                    'fundador_nome': admin_membro.usuario.nome if admin_membro else "N/D",
                    'data_fundacao_formatada': clube.data_criacao.strftime("%B %Y") if clube.data_criacao else "N/D",
                    'membros_count': clube.membros.count(),
                    'leitura_atual_nome': leitura_atual_obj.livro.nome if leitura_atual_obj and leitura_atual_obj.livro else "Nenhuma leitura atual",
                    'match_reason': f"Livro '{leitura.livro.nome}' (status: {leitura.get_status_display()}) corresponde a '{query}'"
                })
    
    contexto = {
        'query': query,
        'resultados': resultados_finais,
        'nome_usuario': request.usuario_logado_obj.nome, # Para o header
    }
    return render(request, 'principal/listagem_resultados.html', contexto)

@login_obrigatorio
def detalhes_clube(request: HttpRequest, clube_id):
    clube = get_object_or_404(Clube, id=clube_id)
    usuario_atual = request.usuario_logado_obj
    
    is_membro = False
    cargo_usuario_atual = None
    membro_info_obj = ClubeMembro.objects.filter(clube=clube, usuario=usuario_atual).first()

    if membro_info_obj:
        is_membro = True
        cargo_usuario_atual = membro_info_obj.cargo

    # Se o clube for privado e o usuário não for membro (e não for admin global do site, se houver essa lógica)
    # você pode querer restringir o acesso aqui, mas por enquanto vamos permitir a visualização
    # e controlar ações como entrar/votar.

    admin_clube_obj = ClubeMembro.objects.filter(clube=clube, cargo=ClubeMembro.Cargo.ADMIN).order_by('data_inscricao').first()
    fundador_nome = admin_clube_obj.usuario.nome if admin_clube_obj else "N/D"

    # Livro do Momento (Lendo Atualmente)
    leitura_do_momento_obj = LeituraClube.objects.filter(
        clube=clube, 
        status=LeituraClube.StatusClube.LENDO_ATUALMENTE
    ).select_related('livro').first()

    # Votação ativa
    votacao_ativa = Votacao.objects.filter(
        clube=clube, 
        data_fim__gte=timezone.now(), 
        is_ativa=True
    ).select_related('clube').prefetch_related('livros_opcoes').order_by('-data_inicio').first()
    
    opcoes_votacao_com_votos = []
    total_votos_na_votacao = 0
    usuario_ja_votou = False

    if votacao_ativa:
        # Cache dos votos para evitar múltiplas queries no loop
        votos_da_votacao = list(VotoUsuario.objects.filter(votacao=votacao_ativa).values_list('livro_votado_id', flat=True))
        total_votos_na_votacao = len(votos_da_votacao)

        for livro_opcao in votacao_ativa.livros_opcoes.all():
            votos_neste_livro = votos_da_votacao.count(livro_opcao.id)
            percentual = (votos_neste_livro / total_votos_na_votacao * 100) if total_votos_na_votacao > 0 else 0
            opcoes_votacao_com_votos.append({
                'livro': livro_opcao,
                'votos': votos_neste_livro,
                'percentual': round(percentual),
                'id': livro_opcao.id 
            })
        if is_membro:
            usuario_ja_votou = VotoUsuario.objects.filter(votacao=votacao_ativa, usuario=usuario_atual).exists()

    membros_do_clube_obj = ClubeMembro.objects.filter(clube=clube).select_related('usuario').order_by('cargo', 'usuario__nome')
    leituras_finalizadas_obj = LeituraClube.objects.filter(clube=clube, status=LeituraClube.StatusClube.FINALIZADO).select_related('livro').order_by('-data_finalizacao')
    
    # Mensagens do Chat (placeholder, já que não será implementado agora)
    # mensagens_chat = Mensagem.objects.filter(clube=clube).select_related('autor').order_by('-data_envio')[:20] 
    mensagens_chat = [] # Vazio por enquanto

    contexto = {
        'clube': clube,
        'fundador_nome': fundador_nome,
        'is_membro': is_membro,
        'cargo_usuario_atual': cargo_usuario_atual,
        'leitura_do_momento_obj': leitura_do_momento_obj,
        'votacao_ativa': votacao_ativa,
        'opcoes_votacao_com_votos': opcoes_votacao_com_votos,
        'total_votos_na_votacao': total_votos_na_votacao,
        'usuario_ja_votou': usuario_ja_votou,
        'membros_do_clube': membros_do_clube_obj,
        'leituras_finalizadas': leituras_finalizadas_obj,
        'mensagens_chat': mensagens_chat,
        'nome_usuario': usuario_atual.nome, # Para o header
        'default_avatar_url': staticfiles_storage.url('img/default_avatar.png'),
        'PrivacidadeChoices': Clube.Privacidade, # Para usar no template: clube.privacidade == PrivacidadeChoices.PUBLICO
        'CargoChoices': ClubeMembro.Cargo, # Para usar no template: cargo_usuario_atual == CargoChoices.ADMIN
    }
    return render(request, 'principal/detalhes_clube.html', contexto)

# --- Views para Ações (você precisará criá-las e suas URLs) ---

@login_obrigatorio
def registrar_voto(request: HttpRequest, clube_id, votacao_id):
    clube = get_object_or_404(Clube, id=clube_id)
    votacao = get_object_or_404(Votacao, id=votacao_id, clube=clube)
    usuario = request.usuario_logado_obj

    if request.method == 'POST':
        livro_id = request.POST.get('livro_votado')
        if not livro_id:
            messages.error(request, "Nenhum livro selecionado para votar.")
            return redirect('principal:detalhes_clube', clube_id=clube_id)

        livro = get_object_or_404(Livro, id=livro_id)

        if not ClubeMembro.objects.filter(clube=clube, usuario=usuario).exists():
            messages.error(request, "Você precisa ser membro do clube para votar.")
            return redirect('principal:detalhes_clube', clube_id=clube_id)

        if VotoUsuario.objects.filter(votacao=votacao, usuario=usuario).exists():
            messages.error(request, "Você já votou nesta votação.")
        elif not votacao.is_ativa or votacao.data_fim < timezone.now():
             messages.error(request, "Esta votação não está mais ativa.")
        elif not livro in votacao.livros_opcoes.all():
            messages.error(request, "Este livro não é uma opção válida para esta votação.")
        else:
            VotoUsuario.objects.create(votacao=votacao, usuario=usuario, livro_votado=livro)
            messages.success(request, f"Seu voto em '{livro.nome}' foi registrado!")
        
        return redirect('principal:detalhes_clube', clube_id=clube_id)
    
    messages.error(request, "Método inválido para registrar voto.")
    return redirect('principal:detalhes_clube', clube_id=clube_id)


@login_obrigatorio
def entrar_clube(request: HttpRequest, clube_id):
    clube = get_object_or_404(Clube, id=clube_id)
    usuario = request.usuario_logado_obj
    if request.method == 'POST':
        if clube.privacidade == Clube.Privacidade.PUBLICO:
            if not ClubeMembro.objects.filter(clube=clube, usuario=usuario).exists():
                # Verificar limite de membros
                if clube.membros.count() < clube.limite_membros:
                    ClubeMembro.objects.create(clube=clube, usuario=usuario, cargo=ClubeMembro.Cargo.MEMBRO)
                    messages.success(request, f"Você entrou no clube '{clube.nome}'!")
                else:
                    messages.error(request, f"O clube '{clube.nome}' atingiu o limite de membros.")
            else:
                messages.info(request, "Você já é membro deste clube.")
        else:
            messages.error(request, "Este clube é privado. A entrada precisa de aprovação.") # Lógica de solicitação seria aqui
        return redirect('principal:detalhes_clube', clube_id=clube_id)
    return redirect('principal:detalhes_clube', clube_id=clube_id) # Ou página de erro/aviso

@login_obrigatorio
def sair_clube(request: HttpRequest, clube_id):
    clube = get_object_or_404(Clube, id=clube_id)
    usuario = request.usuario_logado_obj
    if request.method == 'POST':
        membro = ClubeMembro.objects.filter(clube=clube, usuario=usuario).first()
        if membro:
            # Adicionar lógica para não permitir que o único admin saia, ou transferir admin
            if membro.cargo == ClubeMembro.Cargo.ADMIN and ClubeMembro.objects.filter(clube=clube, cargo=ClubeMembro.Cargo.ADMIN).count() == 1:
                messages.error(request, "Você é o único administrador. Promova outro membro antes de sair ou exclua o clube.")
            else:
                membro.delete()
                messages.success(request, f"Você saiu do clube '{clube.nome}'.")
        else:
            messages.error(request, "Você não é membro deste clube.")
        return redirect('principal:detalhes_clube', clube_id=clube_id)
    return redirect('principal:detalhes_clube', clube_id=clube_id)

@admin_clube_obrigatorio # Este decorator deve passar 'clube' como kwarg
def editar_clube_info(request: HttpRequest, clube_id, clube, **kwargs): # Recebe 'clube'
    # 'clube' é o objeto Clube injetado pelo decorator
    # 'clube_id' da URL ainda está disponível, mas 'clube' é o objeto que usaremos.
    
    # Debug para confirmar
    # print(f"DEBUG: Em editar_clube_info, clube_id da URL: {clube_id}")
    # print(f"DEBUG: Em editar_clube_info, objeto clube recebido: {clube} (ID: {clube.id if clube else 'N/A'})")

    if request.method == 'POST':
        form = ClubeEditForm(request.POST, request.FILES, instance=clube)
        if form.is_valid():
            form.save()
            messages.success(request, "Informações do clube atualizadas com sucesso!")
            return redirect('principal:detalhes_clube', clube_id=clube.id)
        else:
            messages.error(request, "Houve um erro ao atualizar. Verifique os campos.")
    else:
        form = ClubeEditForm(instance=clube)
    
    contexto = {
        'form': form,
        'clube': clube, # Passa o objeto clube para o template
        'nome_usuario': request.usuario_logado_obj.nome,
    }
    return render(request, 'principal/admin/editar_clube.html', contexto)


@admin_clube_obrigatorio
def adicionar_livro_estante_clube(request: HttpRequest, clube_id, clube, **kwargs): # Recebe 'clube'
    if request.method == 'POST':
        form = AdicionarLivroEstanteForm(request.POST, clube=clube) # Passa o objeto clube para o form
        if form.is_valid():
            livro = form.cleaned_data['livro']
            status = form.cleaned_data['status']
            
            if LeituraClube.objects.filter(clube=clube, livro=livro).exists():
                messages.warning(request, f"O livro '{livro.nome}' já está na estante do clube.")
            else:
                LeituraClube.objects.create(clube=clube, livro=livro, status=status)
                messages.success(request, f"Livro '{livro.nome}' adicionado à estante como '{dict(LeituraClube.StatusClube.choices)[status]}'.")
            return redirect('principal:detalhes_clube', clube_id=clube.id)
        else:
            messages.error(request, "Erro ao adicionar livro. Verifique os dados.")
    else:
        form = AdicionarLivroEstanteForm(clube=clube) # Passa o objeto clube para o form para filtrar o queryset de livros
    
    contexto = {
        'clube': clube,
        'form': form,
        'nome_usuario': request.usuario_logado_obj.nome,
    }
    return render(request, 'principal/admin/adicionar_livro_estante.html', contexto)


@admin_clube_obrigatorio
def definir_leitura_atual_clube(request: HttpRequest, clube_id, clube, **kwargs): # Recebe 'clube'
    if request.method == 'POST':
        form = DefinirLeituraAtualForm(request.POST, clube=clube) # Passa o objeto clube para o form
        if form.is_valid():
            leitura_clube_item_selecionado = form.cleaned_data['leitura_clube_item']
            
            LeituraClube.objects.filter(clube=clube, status=LeituraClube.StatusClube.LENDO_ATUALMENTE).exclude(id=leitura_clube_item_selecionado.id).update(status=LeituraClube.StatusClube.A_LER)

            leitura_clube_item_selecionado.status = LeituraClube.StatusClube.LENDO_ATUALMENTE
            # Opcional: adicionar um campo data_inicio_leitura ao modelo LeituraClube
            # leitura_clube_item_selecionado.data_inicio_leitura = timezone.now() 
            leitura_clube_item_selecionado.save()
            
            messages.success(request, f"'{leitura_clube_item_selecionado.livro.nome}' definido como leitura atual do clube.")
            return redirect('principal:detalhes_clube', clube_id=clube.id)
        else:
            messages.error(request, "Erro ao definir leitura atual. Verifique os dados do formulário.")
    else:
        form = DefinirLeituraAtualForm(clube=clube) # Passa o objeto clube para o form para filtrar o queryset

    contexto = {
        'clube': clube,
        'form': form,
        'nome_usuario': request.usuario_logado_obj.nome,
    }
    return render(request, 'principal/admin/definir_leitura_atual.html', contexto)


@admin_clube_obrigatorio
def criar_votacao_clube(request: HttpRequest, clube_id, clube, **kwargs): # Recebe 'clube'
    if request.method == 'POST':
        form = CriarVotacaoForm(request.POST, clube=clube) # Passa o objeto clube para o form
        if form.is_valid():
            Votacao.objects.filter(clube=clube, is_ativa=True).update(is_ativa=False)

            nova_votacao = Votacao(
                clube=clube,
                data_fim=form.cleaned_data['data_fim'],
                is_ativa=True 
            )
            # Se você adicionar um campo título ao modelo Votacao e ao form:
            # if form.cleaned_data.get('titulo_votacao'):
            #    nova_votacao.titulo = form.cleaned_data['titulo_votacao']
            nova_votacao.save()
            nova_votacao.livros_opcoes.set(form.cleaned_data['livros_opcoes'])
            
            messages.success(request, "Nova votação criada com sucesso!")
            return redirect('principal:detalhes_clube', clube_id=clube.id)
        else:
            messages.error(request, "Erro ao criar votação. Verifique os campos.")
    else:
        form = CriarVotacaoForm(clube=clube) # Passa o objeto clube para o form para filtrar queryset
        
    contexto = {
        'clube': clube,
        'form': form,
        'nome_usuario': request.usuario_logado_obj.nome,
    }
    return render(request, 'principal/admin/criarvotacao.html', contexto)