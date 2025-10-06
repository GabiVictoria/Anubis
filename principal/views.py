# anubis/principal/views.py com marcações de tradução

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponseForbidden, JsonResponse
from django.contrib import messages
from django.utils import timezone
from .decorators import login_obrigatorio, admin_clube_obrigatorio
from inicial.models import Clube, ClubeMembro, LeituraClube, Livro, Votacao, VotoUsuario, Mensagem, Usuario, Reuniao, EstantePessoal, generate_unique_id, AvaliacaoLeitura
from django.db import IntegrityError, transaction
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db.models import Q, Avg
from .forms import ClubeEditForm, DefinirLeituraAtualForm, CriarVotacaoForm,  ReuniaoForm, VotacaoEditForm, ConvidarUsuarioForm, PerfilEditForm
import os
import requests
import urllib.parse
from datetime import datetime
from django.utils.translation import gettext as _ 
from django.utils import formats
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

@login_obrigatorio
def home(request: HttpRequest):
    usuario_atual = request.usuario_logado_obj
    query = request.GET.get('q', None)
    leituras_atuais_pessoais = EstantePessoal.objects.filter(usuario=usuario_atual, status=EstantePessoal.StatusLeitura.LENDO).select_related('livro', 'clube') 
    leituras_atuais_formatadas = []
    for leitura in leituras_atuais_pessoais:
        progresso_percentual = 0
        if leitura.progresso_paginas is not None and leitura.livro.paginas and leitura.livro.paginas > 0:
            progresso_percentual = round((leitura.progresso_paginas / leitura.livro.paginas) * 100)
        leituras_atuais_formatadas.append({'livro': leitura.livro, 'clube': leitura.clube, 'percentual': progresso_percentual})
    clubes_do_usuario_qs = usuario_atual.clubes_participados.all()
    if query:
        clubes_do_usuario_qs = clubes_do_usuario_qs.filter(nome__icontains=query)
    clubes_do_usuario_qs = clubes_do_usuario_qs.order_by('nome')
    clubes_info_list = []
    for clube in clubes_do_usuario_qs:
        clube_info = {
            'id': clube.id,
            'nome': clube.nome,
            'descricao': clube.descricao,
            'capa_clube': clube.capa_clube,
            'capa_recomendada': clube.capa_recomendada,
            'data_criacao': clube.data_criacao,
            'membros_count': ClubeMembro.objects.filter(clube=clube).count(),
            'fundador_nome': _("(a definir)"),
            'leitura_atual_nome': None
        }
        admin_membro = ClubeMembro.objects.filter(clube=clube, cargo=ClubeMembro.Cargo.ADMIN).order_by('data_inscricao').first()
        if admin_membro:
            clube_info['fundador_nome'] = admin_membro.usuario.nome
        leitura_atual = LeituraClube.objects.filter(clube=clube, status=LeituraClube.StatusClube.LENDO_ATUALMENTE).select_related('livro').first()
        if leitura_atual and leitura_atual.livro:
            clube_info['leitura_atual_nome'] = leitura_atual.livro.nome
        clubes_info_list.append(clube_info)
    contexto = {
        "nome_usuario": usuario_atual.nome,
        "usuario_logado": True,
        "clubes_do_usuario": clubes_info_list,
        "search_query": query,
        "leituras_atuais": leituras_atuais_formatadas,
    }
    return render(request, 'principal/home.html', contexto)

@login_obrigatorio
def criar_clube(request: HttpRequest):
    context_form_data = {'opcoes_privacidade': Clube.Privacidade.choices, 'opcoes_limite_membros': Clube.LIMITE_MEMBROS_OPCOES}
    if request.method == "POST":
        nome_clube = request.POST.get('nome_clube', '').strip()
        descricao_clube = request.POST.get('descricao_clube', '').strip()
        privacidade_clube_selecionada = request.POST.get('privacidade_clube')
        limite_membros_str_selecionado = request.POST.get('limite_membros')
        capa_clube_file = request.FILES.get('capa_clube')
        capa_recomendada_path_relativo = request.POST.get('capa_recomendada_selecionada')
        context_form_data.update({'nome_clube': nome_clube, 'descricao_clube': descricao_clube, 'privacidade_selecionada': privacidade_clube_selecionada, 'limite_selecionado': limite_membros_str_selecionado})
        if not nome_clube or not descricao_clube:
            messages.error(request, _("O nome e a descrição do clube são obrigatórios."))
            return render(request, 'principal/criar_clube.html', context_form_data)
        if not limite_membros_str_selecionado:
            messages.error(request, _("O limite de membros é obrigatório."))
            return render(request, 'principal/criar_clube.html', context_form_data)
        try:
            limite_membros_int = int(limite_membros_str_selecionado)
        except ValueError:
            messages.error(request, _("Valor inválido para limite de membros."))
            return render(request, 'principal/criar_clube.html', context_form_data)
        if privacidade_clube_selecionada not in [choice[0] for choice in Clube.Privacidade.choices]:
            messages.error(request, _("Opção de privacidade inválida."))
            return render(request, 'principal/criar_clube.html', context_form_data)
        if Clube.objects.filter(nome__iexact=nome_clube).exists():
            messages.error(request, _("Já existe um clube com o nome '%(nome_clube)s'. Por favor, escolha outro nome.") % {'nome_clube': nome_clube})
            return render(request, 'principal/criar_clube.html', context_form_data)
        usuario_criador = request.usuario_logado_obj
        try:
            novo_clube = Clube(nome=nome_clube, descricao=descricao_clube, privacidade=privacidade_clube_selecionada, limite_membros=limite_membros_int)
            if capa_clube_file:
                novo_clube.capa_clube = capa_clube_file
                novo_clube.capa_recomendada = None
            elif capa_recomendada_path_relativo:
                novo_clube.capa_recomendada = capa_recomendada_path_relativo
                novo_clube.capa_clube = None
            novo_clube.save()
            ClubeMembro.objects.create(usuario=usuario_criador, clube=novo_clube, cargo=ClubeMembro.Cargo.ADMIN)
            messages.success(request, _("Clube '%(nome_clube)s' criado com sucesso!") % {'nome_clube': novo_clube.nome})
            return redirect('principal:home')
        except Exception as e:
            messages.error(request, _("Ocorreu um erro inesperado ao criar o clube: %(error)s") % {'error': e})
            return render(request, 'principal/criar_clube.html', context_form_data)
    return render(request, 'principal/criar_clube.html', context_form_data)

@login_obrigatorio
def pagina_de_busca(request: HttpRequest):
    query = request.GET.get('q', '').strip()
    resultados_finais = []
    if query:
        clubes_por_nome = Clube.objects.filter(nome__icontains=query)
        leituras_com_livro_buscado = LeituraClube.objects.filter(Q(livro__nome__icontains=query) & (Q(status=LeituraClube.StatusClube.LENDO_ATUALMENTE))).select_related('clube', 'livro')
        clubes_encontrados_ids = set()
        def processar_clube(clube, razao_match):
            if clube.id not in clubes_encontrados_ids:
                clubes_encontrados_ids.add(clube.id)
                admin_membro = ClubeMembro.objects.filter(clube=clube, cargo=ClubeMembro.Cargo.ADMIN).order_by('data_inscricao').first()
                leitura_atual_obj = LeituraClube.objects.filter(clube=clube, status=LeituraClube.StatusClube.LENDO_ATUALMENTE).select_related('livro').first()
                resultados_finais.append({
                    'id': clube.id, 'nome': clube.nome, 'descricao': clube.descricao, 'capa_clube': clube.capa_clube,
                    'capa_recomendada': clube.capa_recomendada, 'fundador_nome': admin_membro.usuario.nome if admin_membro else _("N/D"),
                    'data_fundacao_formatada': formats.date_format(clube.data_criacao, "F Y") if clube.data_criacao else "",
                    'membros_count': ClubeMembro.objects.filter(clube=clube).count(),
                    'leitura_atual_nome': leitura_atual_obj.livro.nome if leitura_atual_obj and leitura_atual_obj.livro else _("Nenhuma leitura atual"),
                    'match_reason': razao_match
                })
        for clube in clubes_por_nome:
            processar_clube(clube, _("Nome do clube corresponde a '%(query)s'") % {'query': query})
        for leitura in leituras_com_livro_buscado:
            processar_clube(leitura.clube, _("Livro '%(livro_nome)s' corresponde a '%(query)s'") % {'livro_nome': leitura.livro.nome, 'query': query})
    contexto = {'query': query, 'resultados': resultados_finais, 'nome_usuario': request.usuario_logado_obj.nome}
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
    admin_clube_obj = ClubeMembro.objects.filter(clube=clube, cargo=ClubeMembro.Cargo.ADMIN).order_by('data_inscricao').first()
    fundador_nome = admin_clube_obj.usuario.nome if admin_clube_obj else _("N/D")
    leitura_do_momento_obj = LeituraClube.objects.filter(clube=clube, status=LeituraClube.StatusClube.LENDO_ATUALMENTE).select_related('livro').first()
    estante_pessoal_obj = None
    progresso_percentual = 0
    if leitura_do_momento_obj and is_membro:
        try:
            estante_pessoal_obj = EstantePessoal.objects.get(usuario=usuario_atual, livro=leitura_do_momento_obj.livro, clube=clube)
            if estante_pessoal_obj.progresso_paginas and leitura_do_momento_obj.livro.paginas:
                progresso_percentual = round((estante_pessoal_obj.progresso_paginas / leitura_do_momento_obj.livro.paginas) * 100)
        except EstantePessoal.DoesNotExist:
            pass
    votacao_ativa = Votacao.objects.filter(clube=clube, data_fim__gte=timezone.now(), is_ativa=True).select_related('clube').prefetch_related('livros_opcoes').order_by('-data_inicio').first()
    opcoes_votacao_com_votos = []
    total_votos_na_votacao = 0
    usuario_ja_votou = False
    data_fim_votacao_formatada = ""
    if votacao_ativa:
        data_fim_local = timezone.localtime(votacao_ativa.data_fim)
        data_fim_votacao_formatada = formats.date_format(data_fim_local, "d/m/Y H:i")
        votos_da_votacao = list(VotoUsuario.objects.filter(votacao=votacao_ativa).values_list('livro_votado_id', flat=True))
        total_votos_na_votacao = len(votos_da_votacao)
        for livro_opcao in votacao_ativa.livros_opcoes.all():
            votos_neste_livro = votos_da_votacao.count(livro_opcao.id)
            percentual = (votos_neste_livro / total_votos_na_votacao * 100) if total_votos_na_votacao > 0 else 0
            opcoes_votacao_com_votos.append({'livro': livro_opcao, 'votos': votos_neste_livro, 'percentual': round(percentual), 'id': livro_opcao.id})
        if is_membro:
            usuario_ja_votou = VotoUsuario.objects.filter(votacao=votacao_ativa, usuario=usuario_atual).exists()
    
    # --- LINHA CORRIGIDA ---
    # Filtra apenas os membros com os cargos desejados
    cargos_visiveis = [ClubeMembro.Cargo.ADMIN, ClubeMembro.Cargo.MODERADOR, ClubeMembro.Cargo.MEMBRO]
    membros_do_clube_obj = ClubeMembro.objects.filter(clube=clube, cargo__in=cargos_visiveis).select_related('usuario').order_by('cargo', 'usuario__nome')
    
    # --- LINHA CORRIGIDA ---
    # A contagem agora reflete apenas os membros filtrados
    contagem_membros_ativos = membros_do_clube_obj.count()

    leituras_finalizadas_obj = LeituraClube.objects.filter(clube=clube, status=LeituraClube.StatusClube.FINALIZADO).select_related('livro').order_by('-data_finalizacao')
    membro = ClubeMembro.all_objects.filter(clube=clube, usuario=usuario_atual).first()
    data_criacao_formatada = formats.date_format(clube.data_criacao, "F Y") if clube.data_criacao else ""
    reunioes_agendadas = Reuniao.objects.filter(clube=clube, data_horario__gte=timezone.now()).order_by('data_horario')
    contexto = {
        'clube': clube, 'fundador_nome': fundador_nome, 'is_membro': is_membro, 'cargo_usuario_atual': cargo_usuario_atual,
        'contagem_membros_ativos': contagem_membros_ativos, 'leitura_do_momento_obj': leitura_do_momento_obj,
        'votacao_ativa': votacao_ativa, 'opcoes_votacao_com_votos': opcoes_votacao_com_votos,
        'total_votos_na_votacao': total_votos_na_votacao, 'usuario_ja_votou': usuario_ja_votou,
        'membros_do_clube': membros_do_clube_obj, 'leituras_finalizadas': leituras_finalizadas_obj,
        'reunioes_agendadas': reunioes_agendadas, 'nome_usuario': usuario_atual.nome,
        'default_avatar_url': staticfiles_storage.url('img/default_avatar.png'), 'PrivacidadeChoices': Clube.Privacidade,
        'CargoChoices': ClubeMembro.Cargo, 'data_criacao_formatada': data_criacao_formatada,
        'data_fim_votacao_formatada': data_fim_votacao_formatada, 'estante_pessoal_obj': estante_pessoal_obj,
        'progresso_percentual': progresso_percentual, "membro": membro,
    }
    return render(request, 'principal/detalhes_clube.html', contexto)

@login_obrigatorio
def registrar_voto(request: HttpRequest, clube_id, votacao_id):
    clube = get_object_or_404(Clube, id=clube_id)
    votacao = get_object_or_404(Votacao, id=votacao_id, clube=clube)
    usuario = request.usuario_logado_obj
    if request.method == 'POST':
        livro_id = request.POST.get('livro_votado')
        if not livro_id:
            messages.error(request, _("Nenhum livro selecionado para votar."))
            return redirect('principal:detalhes_clube', clube_id=clube_id)
        livro = get_object_or_404(Livro, id=livro_id)
        if not ClubeMembro.objects.filter(clube=clube, usuario=usuario).exists():
            messages.error(request, _("Você precisa ser membro do clube para votar."))
            return redirect('principal:detalhes_clube', clube_id=clube_id)
        if VotoUsuario.objects.filter(votacao=votacao, usuario=usuario).exists():
            messages.error(request, _("Você já votou nesta votação."))
        elif not votacao.is_ativa or votacao.data_fim < timezone.now():
            messages.error(request, _("Esta votação não está mais ativa."))
        elif not livro in votacao.livros_opcoes.all():
            messages.error(request, _("Este livro não é uma opção válida para esta votação."))
        else:
            VotoUsuario.objects.create(votacao=votacao, usuario=usuario, livro_votado=livro)
            messages.success(request, _("Seu voto em '%(livro_nome)s' foi registrado!") % {'livro_nome': livro.nome})
        return redirect('principal:detalhes_clube', clube_id=clube_id)
    messages.error(request, _("Método inválido para registrar voto."))
    return redirect('principal:detalhes_clube', clube_id=clube_id)

@login_obrigatorio
def entrar_clube(request: HttpRequest, clube_id):
    clube = get_object_or_404(Clube, id=clube_id)
    usuario = request.usuario_logado_obj
    if request.method == 'POST':
        if clube.privacidade == 'PRIVADO':
            return redirect('principal:solicitar_entrada_privado', clube_id=clube.id)
        membro_existente = ClubeMembro.all_objects.filter(clube=clube, usuario=usuario).first()
        if membro_existente:
            if membro_existente.cargo == ClubeMembro.Cargo.BANIDO:
                messages.error(request, _("Você foi banido deste clube e não pode entrar novamente."))
                return redirect('principal:detalhes_clube', clube_id=clube.id)
            if not membro_existente.deleted:
                messages.info(request, _("Você já é membro deste clube."))
                return redirect('principal:detalhes_clube', clube_id=clube.id)
        if clube.membros.count() >= clube.limite_membros:
            messages.error(request, _("O clube '%(nome_clube)s' está lotado.") % {'nome_clube': clube.nome})
            return redirect('principal:detalhes_clube', clube_id=clube_id)
        membro, created = ClubeMembro.all_objects.update_or_create(clube=clube, usuario=usuario, defaults={'deleted': None, 'cargo': ClubeMembro.Cargo.MEMBRO})
        if created:
            messages.success(request, _("Você entrou no clube com sucesso!"))
        else:
            messages.success(request, _("Bem-vindo(a) de volta ao clube!"))
    return redirect('principal:detalhes_clube', clube_id=clube.id)

@login_obrigatorio
def solicitar_entrada_privado(request: HttpRequest, clube_id):
    clube = get_object_or_404(Clube, id=clube_id)
    usuario = request.usuario_logado_obj
    if request.method == 'POST':
        membro_existente = ClubeMembro.all_objects.filter(clube=clube, usuario=usuario).first()
        if membro_existente:
            if membro_existente.cargo == ClubeMembro.Cargo.BANIDO:
                messages.error(request, _("Você foi banido deste clube e não pode solicitar entrada."))
                return redirect('principal:detalhes_clube', clube_id=clube.id)
            if not membro_existente.deleted:
                messages.info(request, _("Você já é membro ou já solicitou entrada."))
                return redirect('principal:detalhes_clube', clube_id=clube.id)
        if clube.membros.count() >= clube.limite_membros:
            messages.error(request, _("O clube '%(nome_clube)s' está lotado e não pode aceitar novas solicitações.") % {'nome_clube': clube.nome})
            return redirect('principal:detalhes_clube', clube_id=clube.id)
        ClubeMembro.all_objects.update_or_create(clube=clube, usuario=usuario, defaults={'deleted': None, 'cargo': ClubeMembro.Cargo.PENDENTE})
        messages.success(request, _("Sua solicitação foi enviada ao administrador do clube."))
    return redirect('principal:detalhes_clube', clube_id=clube.id)

@login_obrigatorio
def sair_clube(request: HttpRequest, clube_id):
    clube = get_object_or_404(Clube, id=clube_id)
    usuario = request.usuario_logado_obj
    if request.method == 'POST':
        membro = ClubeMembro.objects.filter(clube=clube, usuario=usuario).first()
        if membro:
            if membro.cargo == ClubeMembro.Cargo.ADMIN and ClubeMembro.objects.filter(clube=clube, cargo=ClubeMembro.Cargo.ADMIN).count() == 1:
                messages.error(request, _("Você é o único administrador. Promova outro membro antes de sair ou exclua o clube."))
            else:
                membro.delete()
                messages.success(request, _("Você saiu do clube '%(nome_clube)s'.") % {'nome_clube': clube.nome})
        else:
            messages.error(request, _("Você não é membro deste clube."))
    return redirect('principal:home')

@admin_clube_obrigatorio
def editar_clube(request: HttpRequest, clube, **kwargs):
    if request.method == 'POST':
        form = ClubeEditForm(request.POST, request.FILES, instance=clube)
        if form.is_valid():
            clube_editado = form.save(commit=False)
            if not clube_editado.unique_id:
                clube_editado.unique_id = generate_unique_id(prefix='#')
            capa_clube_file = request.FILES.get('capa_clube')
            capa_recomendada_path = request.POST.get('capa_recomendada_selecionada')
            if capa_clube_file:
                clube_editado.capa_clube = capa_clube_file
                clube_editado.capa_recomendada = None
            elif capa_recomendada_path:
                clube_editado.capa_recomendada = capa_recomendada_path
                if clube_editado.capa_clube:
                    clube_editado.capa_clube.delete(save=False)
            clube_editado.save()
            messages.success(request, _("O clube '%(nome_clube)s' foi atualizado com sucesso!") % {'nome_clube': clube.nome})
            return redirect('principal:detalhes_clube', clube_id=clube.id)
        else:
            messages.error(request, _("Houve um erro no formulário. Por favor, verifique os dados."))
    else:
        form = ClubeEditForm(instance=clube)
    membros_candidatos = ClubeMembro.objects.filter(clube=clube).exclude(usuario=request.usuario_logado_obj).select_related('usuario')
    contexto = {'form': form, 'clube': clube, 'nome_usuario': request.usuario_logado_obj.nome, 'membros_candidatos': membros_candidatos}
    return render(request, 'principal/admin/editar_clube.html', contexto)

@admin_clube_obrigatorio
def excluir_clube(request: HttpRequest, clube, **kwargs):
    if request.method == 'POST':
        nome_clube = clube.nome
        clube.delete()
        messages.success(request, _("O clube '%(nome_clube)s' foi desativado com sucesso e não aparecerá mais nas buscas.") % {'nome_clube': nome_clube})
        return redirect('principal:home')
    else:
        messages.error(request, _("Ação inválida."))
        return redirect('principal:detalhes_clube', clube_id=clube.id)


@login_obrigatorio
@transaction.atomic
def transferir_admin_clube(request: HttpRequest, clube_id):
    clube = get_object_or_404(Clube, id=clube_id)
    usuario_atual = request.usuario_logado_obj
    
    if request.method != 'POST':
        messages.error(request, _("Ação inválida."))
        return redirect('principal:detalhes_clube', clube_id=clube.id)

    try:
        membro_atual_admin = ClubeMembro.objects.get(clube=clube, usuario=usuario_atual, cargo=ClubeMembro.Cargo.ADMIN)
    except ClubeMembro.DoesNotExist:
        messages.error(request, _("Você não tem permissão para realizar esta ação."))
        return redirect('principal:detalhes_clube', clube_id=clube.id)

    novo_admin_id = request.POST.get('novo_admin_id')
    if not novo_admin_id:
        messages.error(request, _("Você deve selecionar um membro para ser o novo administrador."))
        return redirect('principal:editar_clube', clube_id=clube.id)

    try:
        membro_novo_admin = ClubeMembro.objects.get(clube=clube, usuario_id=novo_admin_id)
    except ClubeMembro.DoesNotExist:
        messages.error(request, _("O membro selecionado não é válido."))
        return redirect('principal:editar_clube', clube_id=clube.id)

    membro_novo_admin.cargo = ClubeMembro.Cargo.ADMIN
    membro_novo_admin.save()
    membro_atual_admin.cargo = ClubeMembro.Cargo.MEMBRO
    membro_atual_admin.save()

    messages.success(request, _("Cargo de administrador transferido com sucesso para %(nome_usuario)s. Você agora é um membro comum.") % {'nome_usuario': membro_novo_admin.usuario.nome})
    return redirect('principal:detalhes_clube', clube_id=clube.id)

@login_obrigatorio
def buscar_livros_api(request: HttpRequest):
    title_query = request.GET.get('title', '').strip()
    author_query = request.GET.get('author', '').strip()
    page = int(request.GET.get('page', '1'))

    if not title_query and not author_query:
        return JsonResponse({'error': _('Forneça um título ou autor para a busca.')}, status=400)

    livros_encontrados = {}
    google_total_items = 0

    try:
        google_api_key = getattr(settings, 'GOOGLE_BOOKS_API_KEY', None)
        if google_api_key:
            query_parts = []
            if title_query:
                query_parts.append(f'intitle:{title_query}')
            if author_query:
                query_parts.append(f'inauthor:{author_query}')
            
            google_query = '+'.join(query_parts)
            start_index = (page - 1) * 15
            google_url = f"https://www.googleapis.com/books/v1/volumes?q={urllib.parse.quote(google_query)}&orderBy=relevance&maxResults=15&startIndex={start_index}&key={google_api_key}"
            
            response_google = requests.get(google_url, timeout=15)
            response_google.raise_for_status()
            data_google = response_google.json()
            google_total_items = data_google.get('totalItems', 0)

            for item in data_google.get('items', []):
                volume_info = item.get('volumeInfo', {})
                if not volume_info.get('pageCount') or volume_info.get('pageCount') <= 0:
                    continue
                isbn13 = None
                for identifier in volume_info.get('industryIdentifiers', []):
                    if identifier.get('type') == 'ISBN_13':
                        isbn13 = identifier.get('identifier')
                        break
                if isbn13:
                    livros_encontrados[isbn13] = {
                        'isbn13': isbn13,
                        'titulo': volume_info.get('title', _('Título indisponível')),
                        'autores': volume_info.get('authors', [_('Autor desconhecido')]),
                        'data_publicacao': volume_info.get('publishedDate', '')[:4] if volume_info.get('publishedDate') else None,
                        'paginas': volume_info.get('pageCount'), 
                        'capa': volume_info.get('imageLinks', {}).get('thumbnail', None)
                    }
    except requests.exceptions.RequestException as e:
        print(f"AVISO: Erro ao buscar no Google Books API: {e}")

    try:
        params = {'limit': 15, 'page': page}
        if title_query:
            params['title'] = title_query
        if author_query:
            params['author'] = author_query
        params['language'] = 'por'
        
        query_string = urllib.parse.urlencode(params)
        url_ol = f"https://openlibrary.org/search.json?{query_string}&fields=key,title,author_name,cover_i,first_publish_year,number_of_pages_median,isbn"
        
        response_ol = requests.get(url_ol, timeout=15)
        response_ol.raise_for_status()
        data_ol = response_ol.json()

        for doc in data_ol.get('docs', []):
            if not doc.get('number_of_pages_median') or doc.get('number_of_pages_median') <= 0:
                continue
            isbn13 = None
            if doc.get('isbn'):
                for i in doc.get('isbn', []):
                    if len(i) == 13 and i.isdigit():
                        isbn13 = i
                        break
            if isbn13:
                livro_novo_ol = {
                    'isbn13': isbn13,
                    'titulo': doc.get('title', _('Título indisponível')),
                    'autores': doc.get('author_name', [_('Autor desconhecido')]),
                    'data_publicacao': doc.get('first_publish_year', None),
                    'paginas': doc.get('number_of_pages_median'), 
                    'capa': f"https://covers.openlibrary.org/b/id/{doc.get('cover_i')}-L.jpg" if doc.get('cover_i') else None
                }
                livro_existente = livros_encontrados.get(isbn13)
                if not livro_existente or (livro_novo_ol['capa'] and not livro_existente['capa']):
                    livros_encontrados[isbn13] = livro_novo_ol
    except requests.exceptions.RequestException as e:
        print(f"AVISO: Erro ao buscar na Open Library API: {e}")

    livros_combinados = list(livros_encontrados.values())
    livros_formatados = sorted(livros_combinados, key=lambda livro: livro.get('capa') is not None, reverse=True)

    response_data = {
        'livros': livros_formatados,
        'totalItems': google_total_items,
        'page': page
    }
    return JsonResponse(response_data)

@admin_clube_obrigatorio
def adicionar_livro_estante_clube(request: HttpRequest, clube, **kwargs):
    contexto = {
        'clube': clube,
        'nome_usuario': request.usuario_logado_obj.nome,
    }
    return render(request, 'principal/admin/adicionar_livro_estante.html', contexto)

@admin_clube_obrigatorio
def adicionar_livro_api_para_estante(request: HttpRequest, clube, **kwargs):
    if request.method == 'POST':
        isbn13 = request.POST.get('isbn13')
        titulo = request.POST.get('titulo')
        autores = request.POST.get('autores')
        paginas = request.POST.get('paginas')
        capa_url = request.POST.get('capa')
        ano_publicacao = request.POST.get('data_publicacao')

        if not all([isbn13, titulo, autores]):
            messages.error(request, _("Dados do livro incompletos (ISBN obrigatório)."))
            return redirect('principal:adicionar_livro_estante_clube', clube_id=clube.id)

        paginas_int = int(paginas) if paginas and paginas.isdigit() else None
        data_publicacao_obj = None
        if ano_publicacao and ano_publicacao.isdigit():
            data_publicacao_obj = datetime(int(ano_publicacao), 1, 1).date()

        livro, created = Livro.objects.get_or_create(
            isbn13=isbn13,
            defaults={
                'nome': titulo,
                'autor': autores,
                'paginas': paginas_int,
                'data_publicacao': data_publicacao_obj
            }
        )
        
        if LeituraClube.objects.filter(clube=clube, livro=livro).exists():
            messages.warning(request, _("O livro '%(livro_nome)s' já está na estante do clube.") % {'livro_nome': livro.nome})
        else:
            LeituraClube.objects.create(clube=clube, livro=livro, status=LeituraClube.StatusClube.A_LER)
            messages.success(request, _("Livro '%(livro_nome)s' adicionado à estante com sucesso!") % {'livro_nome': livro.nome})

            if not livro.capa and capa_url and 'None' not in capa_url:
                try:
                    img_response = requests.get(capa_url, timeout=10)
                    if img_response.status_code == 200:
                        file_name = f"{livro.isbn13}.jpg"
                        livro.capa.save(file_name, ContentFile(img_response.content), save=True)
                except Exception as e:
                    print(f"AVISO: Não foi possível baixar a capa para o livro {livro.isbn13}. Erro: {e}")

    return redirect('principal:detalhes_clube', clube_id=clube.id)

@admin_clube_obrigatorio
def definir_leitura_atual_clube(request: HttpRequest, clube, **kwargs):
    if request.method == 'POST':
        form = DefinirLeituraAtualForm(request.POST, clube=clube)
        if form.is_valid():
            leitura_clube_item_selecionado = form.cleaned_data['leitura_clube_item']
            LeituraClube.objects.filter(clube=clube, status=LeituraClube.StatusClube.LENDO_ATUALMENTE).exclude(id=leitura_clube_item_selecionado.id).update(status=LeituraClube.StatusClube.A_LER)
            leitura_clube_item_selecionado.status = LeituraClube.StatusClube.LENDO_ATUALMENTE
            leitura_clube_item_selecionado.save()
            messages.success(request, _("'%(livro_nome)s' definido como leitura atual do clube.") % {'livro_nome': leitura_clube_item_selecionado.livro.nome})
            return redirect('principal:detalhes_clube', clube_id=clube.id)
        else:
            messages.error(request, _("Erro ao definir leitura atual. Verifique os dados do formulário."))
    else:
        form = DefinirLeituraAtualForm(clube=clube)

    contexto = {
        'clube': clube,
        'form': form,
        'nome_usuario': request.usuario_logado_obj.nome,
    }
    return render(request, 'principal/admin/definir_leitura_atual.html', contexto)



@admin_clube_obrigatorio
def criar_votacao_clube(request: HttpRequest, clube, **kwargs):

    if request.method == 'POST':
        form = CriarVotacaoForm(request.POST, clube=clube)
        if form.is_valid():
            Votacao.objects.filter(clube=clube, is_ativa=True).update(is_ativa=False)
            nova_votacao = form.save(commit=False)
            nova_votacao.clube = clube
            nova_votacao.is_ativa = True
            nova_votacao.save()
            livros_selecionados = form.cleaned_data['livros_opcoes']
            nova_votacao.livros_opcoes.set(livros_selecionados)
            messages.success(request, _("Nova votação criada com sucesso!"))
            return redirect('principal:detalhes_clube', clube_id=clube.id)
        else:
            for field, error_list in form.errors.items():
                for error in error_list:
                    messages.error(request, f"{error}")
    else:
        form = CriarVotacaoForm(clube=clube)
    contexto = {'form': form, 'clube': clube, 'nome_usuario': request.usuario_logado_obj.nome}
    return render(request, 'principal/admin/criarvotacao.html', contexto)

@login_obrigatorio
def perfil(request):
    usuario = request.usuario_logado_obj

    livros_lidos_recentemente = EstantePessoal.objects.filter(
        usuario=usuario,
        status=EstantePessoal.StatusLeitura.LIDO
    ).order_by('-id')[:5]


    clubes_membro = ClubeMembro.objects.filter(
        usuario=usuario,
        cargo__in=[ClubeMembro.Cargo.MEMBRO, ClubeMembro.Cargo.ADMIN, ClubeMembro.Cargo.MODERADOR]
    ).order_by('-data_inscricao')[:5].select_related('clube')

    clubes_recentes_data = []
    for membro_info in clubes_membro:
        clube = membro_info.clube
       
        admin_membro = ClubeMembro.objects.filter(clube=clube, cargo=ClubeMembro.Cargo.ADMIN).first()
        
        leitura_atual = LeituraClube.objects.filter(clube=clube, status=LeituraClube.StatusClube.LENDO_ATUALMENTE).first()
        
        clubes_recentes_data.append({
            'clube_obj': clube,
            'data_entrada': membro_info.data_inscricao,
            'admin_nome': admin_membro.usuario.nome if admin_membro else None,
            'livro_atual': leitura_atual.livro.nome if leitura_atual else None,
            'proximo_livro': None,
        })

    contexto = {
        'usuario': usuario,
        'clubes_recentes': clubes_recentes_data,
        'livros_lidos_recentemente': livros_lidos_recentemente
    }
    return render(request, 'principal/perfil.html', contexto)

# busca de perfil
@login_obrigatorio
def perfil_usuario(request, user_id):
    
    usuario_perfil = get_object_or_404(Usuario, unique_id=f"@{user_id}")
    

    contexto = {
        'usuario_perfil': usuario_perfil
    }
    return render(request, 'principal/perfil_usuario.html', contexto)

@login_obrigatorio
def editar_perfil(request: HttpRequest):
    """Página para o usuário logado editar suas informações de perfil."""
    usuario = request.usuario_logado_obj
    if request.method == 'POST':
        # Passamos o request.FILES para lidar com o upload de imagens
        form = PerfilEditForm(request.POST, request.FILES, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, _("Perfil atualizado com sucesso!"))
            return redirect('principal:perfil')
        else:
            messages.error(request, _("Houve um erro no formulário. Por favor, verifique os dados."))
    else:
        form = PerfilEditForm(instance=usuario)

    contexto = {
        'form': form,
    }
    return render(request, 'principal/editar_perfil.html', contexto)

@login_obrigatorio
def estante(request, clube_id):
    clube = get_object_or_404(Clube, id=clube_id)
    leitura_atual = LeituraClube.objects.filter(clube=clube, status=LeituraClube.StatusClube.LENDO_ATUALMENTE).select_related('livro').first()
    proxima_reuniao = None
    if leitura_atual:
        proxima_reuniao = Reuniao.objects.filter(clube=clube, data_horario__gte=timezone.now()).order_by('data_horario').first() 
    contexto = {'clube': clube, 'leitura_atual': leitura_atual, 'proxima_reuniao': proxima_reuniao}
    return render(request, 'principal/estante.html', contexto)

@login_obrigatorio
def lidos_view(request, clube_id):
    clube = get_object_or_404(Clube, id=clube_id)
    
    lidos = LeituraClube.objects.filter(
        clube=clube, 
        status=LeituraClube.StatusClube.FINALIZADO
    ).select_related('livro')

    contexto = {
        'clube': clube,
        'lidos': lidos
    }
    return render(request, 'principal/lidos.html', contexto) 

@login_obrigatorio
def abandonados_view(request, clube_id):
    clube = get_object_or_404(Clube, id=clube_id)
    
    abandonado = LeituraClube.objects.filter(
        clube=clube, 
        status=LeituraClube.StatusClube.ABANDONADO
    ).select_related('livro')

    contexto = {
        'clube': clube,
        'abandonado': abandonado
    }
   
    return render(request, 'principal/abandonados.html', contexto) 

@login_obrigatorio
def queremos_ler_view(request, clube_id):
    clube = get_object_or_404(Clube, id=clube_id)
    
    leituras_a_ler = LeituraClube.objects.filter(
        clube=clube, 
        status=LeituraClube.StatusClube.A_LER
    ).select_related('livro')

    contexto = {
        'clube': clube,
        'leituras_a_ler': leituras_a_ler
    }
    
    return render(request, 'principal/queremos_ler.html', contexto)


@login_obrigatorio
@require_POST
def alterar_status_livro(request, clube_id, leitura_id):
    if not ClubeMembro.objects.filter(clube_id=clube_id, usuario=request.usuario_logado_obj, cargo=ClubeMembro.Cargo.ADMIN).exists():
        return JsonResponse({'success': False, 'level': 'error', 'message': 'Permissão negada'}, status=403)

    try:
        data = json.loads(request.body)
        novo_status = data.get('status')
        data_finalizacao_str = data.get('data_finalizacao') 

        if novo_status not in LeituraClube.StatusClube.values:
            return JsonResponse({'success': False, 'level': 'error', 'message': 'Status inválido'}, status=400)

        leitura = get_object_or_404(LeituraClube, id=leitura_id, clube_id=clube_id)

        
        if novo_status == LeituraClube.StatusClube.LENDO_ATUALMENTE:
            LeituraClube.objects.filter(
                clube_id=clube_id, 
                status=LeituraClube.StatusClube.LENDO_ATUALMENTE
            ).exclude(id=leitura_id).update(status=LeituraClube.StatusClube.A_LER)
        
        
        if novo_status == LeituraClube.StatusClube.FINALIZADO:
            if not data_finalizacao_str:
                return JsonResponse({'success': False, 'level': 'error', 'message': 'Para finalizar um livro, a data de finalização é obrigatória.'}, status=400)
            try:
                # Converte a string de data para um objeto de data do Python
                leitura.data_finalizacao = datetime.strptime(data_finalizacao_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'success': False, 'level': 'error', 'message': 'Formato de data inválido. Use AAAA-MM-DD.'}, status=400)
        else:
            # Garante que a data de finalização seja limpa se o status não for 'FINALIZADO'
            leitura.data_finalizacao = None

        leitura.status = novo_status
        leitura.save()
        
        return JsonResponse({
            'success': True,
            'level': 'success',
            'message': _('Status do livro atualizado com sucesso!')
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'level': 'error', 'message': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'level': 'error', 'message': str(e)}, status=500)
    


@login_obrigatorio
@require_POST 
def atualizar_progresso(request: HttpRequest, estante_pessoal_id):
 
    estante_entry = get_object_or_404(EstantePessoal, id=estante_pessoal_id, usuario=request.usuario_logado_obj)
    
    try:
        data = json.loads(request.body)
        paginas_lidas = int(data.get('paginas_lidas', estante_entry.progresso_paginas))
        finalizado = data.get('finalizado', False)

        total_paginas = estante_entry.livro.paginas

        # Validação de páginas lidas
        if total_paginas and (paginas_lidas < 0 or paginas_lidas > total_paginas):
            message_text = _('Número de páginas inválido.')
            messages.error(request, message_text)
            return JsonResponse({'success': False, 'message': str(message_text), 'level': 'error'}, status=400)

        is_100_percent = total_paginas is not None and paginas_lidas >= total_paginas

        if finalizado or is_100_percent:
            estante_entry.progresso_paginas = total_paginas
            estante_entry.status = EstantePessoal.StatusLeitura.LIDO
            
            message_text = _('Leitura finalizada com sucesso!')
            messages.success(request, message_text)
            
            response_data = {
                'success': True,
                'message': str(message_text),
                'level': 'success',
                'show_rating_modal': False
            }
            leitura_do_clube = LeituraClube.objects.filter(clube=estante_entry.clube, livro=estante_entry.livro).first()
            if leitura_do_clube:
                ja_avaliou = AvaliacaoLeitura.objects.filter(leitura_clube=leitura_do_clube, usuario=request.usuario_logado_obj).exists()
                if leitura_do_clube.status == LeituraClube.StatusClube.LENDO_ATUALMENTE and not ja_avaliou:
                    response_data['show_rating_modal'] = True
                    response_data['leitura_clube_id'] = leitura_do_clube.id
            
            estante_entry.save()
            return JsonResponse(response_data)

        estante_entry.progresso_paginas = paginas_lidas
        estante_entry.save()
        
        message_text = _('Progresso atualizado!')
        messages.success(request, message_text)
        return JsonResponse({'success': True, 'message': str(message_text), 'level': 'success'})

    except json.JSONDecodeError:
        message_text = _('Erro nos dados enviados.')
        messages.error(request, message_text)
        return JsonResponse({'success': False, 'message': str(message_text), 'level': 'error'}, status=400)
    except Exception as e:
        message_text = _('Ocorreu um erro inesperado ao atualizar o progresso.')
        messages.error(request, str(e)) # Log do erro real no backend
        return JsonResponse({'success': False, 'message': str(message_text), 'level': 'error'}, status=500)


@login_obrigatorio
@require_POST
def registrar_nota_clube(request: HttpRequest, leitura_id):
    """
    Salva a nota do usuário tanto na avaliação do clube quanto na sua estante pessoal,
    e recalcula a média do clube.
    """
    try:
        leitura_clube = get_object_or_404(LeituraClube, id=leitura_id)
        usuario = request.usuario_logado_obj
        
        if not ClubeMembro.objects.filter(clube=leitura_clube.clube, usuario=usuario).exists():
            message_text = _('Você não é membro deste clube.')
            messages.error(request, message_text)
            return JsonResponse({'success': False, 'message': str(message_text), 'level': 'error'}, status=403)

        data = json.loads(request.body)
        nota = float(data.get('nota'))

        # Validação da nota
        if not (0 <= nota <= 5):
            message_text = _('A nota deve ser um valor entre 0 e 5.')
            messages.error(request, message_text)
            return JsonResponse({'success': False, 'message': str(message_text), 'level': 'error'}, status=400)
        
        # --- INÍCIO DA MODIFICAÇÃO ---

        # 1. Atualiza a nota na Estante Pessoal do usuário
        try:
            estante_pessoal_entry = EstantePessoal.objects.get(
                usuario=usuario,
                livro=leitura_clube.livro,
                clube=leitura_clube.clube
            )
            estante_pessoal_entry.nota_pessoal = nota
            estante_pessoal_entry.save()
        except EstantePessoal.DoesNotExist:
            # Se por algum motivo o livro não estiver na estante pessoal,
            # a avaliação do clube ainda prosseguirá sem erros.
            pass 

        # --- FIM DA MODIFICAÇÃO ---

        # 2. Cria ou atualiza a avaliação para o clube
        AvaliacaoLeitura.objects.update_or_create(
            leitura_clube=leitura_clube,
            usuario=usuario,
            defaults={'nota': nota}
        )

        # 3. Recalcula a nota média do clube
        nova_media = AvaliacaoLeitura.objects.filter(leitura_clube=leitura_clube).aggregate(Avg('nota'))['nota__avg']
        leitura_clube.nota_media_clube = round(nova_media, 1) if nova_media else None
        leitura_clube.save()

        message_text = _('Sua avaliação foi registrada. Obrigado!')
        messages.success(request, message_text)
        return JsonResponse({'success': True, 'message': str(message_text), 'level': 'success'})

    except json.JSONDecodeError:
        message_text = _('Erro nos dados enviados.')
        messages.error(request, message_text)
        return JsonResponse({'success': False, 'message': str(message_text), 'level': 'error'}, status=400)
    except Exception as e:
        message_text = _('Ocorreu um erro inesperado ao salvar sua avaliação.')
        messages.error(request, str(e)) # Log do erro real
        return JsonResponse({'success': False, 'message': str(message_text), 'level': 'error'}, status=500)



@admin_clube_obrigatorio
def criar_reuniao(request: HttpRequest, clube, **kwargs):
    # Esta view não precisa de alteração de fuso horário, pois cria um novo objeto.
    # A lógica de tratamento de erros já está correta.
    if request.method == 'POST':
        form = ReuniaoForm(request.POST, clube=clube)
        if form.is_valid():
            reuniao = form.save(commit=False)
            reuniao.clube = clube
            reuniao.save()
            messages.success(request, _("Reunião agendada com sucesso!"))
            return redirect('principal:detalhes_clube', clube_id=clube.id)
        else:
            for field, error_list in form.errors.items():
                for error in error_list:
                    messages.error(request, error)
    else:
        form = ReuniaoForm(clube=clube)
        
    contexto = {'form': form, 'clube': clube, 'form_title': _('Agendar Nova Reunião')}
    return render(request, 'principal/admin/gerenciar_reuniao.html', contexto)

@admin_clube_obrigatorio
def editar_reuniao(request: HttpRequest, clube, reuniao_id, **kwargs):
    reuniao = get_object_or_404(Reuniao, id=reuniao_id, clube=clube)
    if request.method == 'POST':
        form = ReuniaoForm(request.POST, instance=reuniao, clube=clube)
        if form.is_valid():
            form.save()
            messages.success(request, _("Reunião atualizada com sucesso!"))
            return redirect('principal:detalhes_clube', clube_id=clube.id)
        else:
            # Garante que os erros de validação sejam exibidos
            for field, error_list in form.errors.items():
                for error in error_list:
                    messages.error(request, error)
    else:
        # --- LÓGICA DE FUSO HORÁRIO APLICADA AQUI, NA VIEW ---
        # 1. Converte a data do banco (UTC) para o fuso horário local
        data_horario_local = timezone.localtime(reuniao.data_horario)

        # 2. Prepara um dicionário com os dados iniciais para o formulário
        initial_data = {
            'titulo': reuniao.titulo,
            'data_horario': data_horario_local,
            # (outros campos são preenchidos pela 'instance')
        }
        # 3. Inicia o formulário com a instância E os dados iniciais corrigidos
        form = ReuniaoForm(instance=reuniao, clube=clube, initial=initial_data)

    contexto = {
        'form': form, 
        'clube': clube, 
        'reuniao': reuniao, 
        'form_title': _('Editar Reunião')
    }
    return render(request, 'principal/admin/gerenciar_reuniao.html', contexto)

@admin_clube_obrigatorio
def editar_votacao(request: HttpRequest, clube, votacao_id, **kwargs): 
    votacao = get_object_or_404(Votacao, id=votacao_id, clube=clube)

    if request.method == 'POST':
        form = VotacaoEditForm(request.POST, instance=votacao)
        if form.is_valid():
            form.save()
            messages.success(request, _("Votação atualizada com sucesso!"))
            return redirect('principal:detalhes_clube', clube_id=clube.id)
        else:
            for field, error_list in form.errors.items():
                for error in error_list:
                    messages.error(request, error)
    else:
        # --- LÓGICA DE FUSO HORÁRIO APLICADA AQUI, NA VIEW ---
        # 1. Converte a data do banco (UTC) para o fuso horário local
        data_fim_local = timezone.localtime(votacao.data_fim)

        # 2. Prepara um dicionário com os dados iniciais para o formulário
        initial_data = {
            'titulo': votacao.titulo,
            'data_fim': data_fim_local, # Usa a data já convertida
        }
        # 3. Inicia o formulário com os dados da instância E os dados iniciais corrigidos
        form = VotacaoEditForm(instance=votacao, initial=initial_data)
        
    contexto = {
        'form': form, 
        'clube': clube, 
        'votacao': votacao
    }
    return render(request, 'principal/admin/editar_votacao.html', contexto)
@admin_clube_obrigatorio
def fechar_votacao(request: HttpRequest, clube, votacao_id, **kwargs):
    if request.method == 'POST':
        votacao = get_object_or_404(Votacao, id=votacao_id, clube=clube)
        votacao.is_ativa = False
        votacao.data_fim = timezone.now()
        votacao.save()
        messages.success(request, _("A votação foi fechada manualmente."))
    return redirect('principal:detalhes_clube', clube_id=clube.id)

@login_obrigatorio
def iniciar_leitura(request: HttpRequest, clube_id, livro_id):
    if request.method == 'POST':
        clube = get_object_or_404(Clube, id=clube_id)
        livro = get_object_or_404(Livro, id=livro_id)
        usuario = request.usuario_logado_obj
        if not ClubeMembro.objects.filter(clube=clube, usuario=usuario).exists():
            messages.error(request, _("Você precisa ser membro do clube para iniciar uma leitura."))
            return redirect('principal:detalhes_clube', clube_id=clube_id)
        EstantePessoal.objects.get_or_create(
            usuario=usuario,
            livro=livro,
            clube=clube,
            defaults={'status': EstantePessoal.StatusLeitura.LENDO, 'progresso_paginas': 0}
        )
        messages.success(request, _("Leitura de '%(livro_nome)s' iniciada!") % {'livro_nome': livro.nome})
    return redirect('principal:detalhes_clube', clube_id=clube_id)


@admin_clube_obrigatorio
def gerenciar_membros(request: HttpRequest, clube, **kwargs):
    """Página principal de gerenciamento de membros para o admin."""
    solicitacoes_pendentes = ClubeMembro.objects.filter(clube=clube, cargo=ClubeMembro.Cargo.PENDENTE).select_related('usuario')
    moderadores = ClubeMembro.objects.filter(clube=clube, cargo=ClubeMembro.Cargo.MODERADOR).select_related('usuario')
    membros_comuns = ClubeMembro.objects.filter(clube=clube, cargo=ClubeMembro.Cargo.MEMBRO).select_related('usuario')
    membros_banidos = ClubeMembro.all_objects.filter(clube=clube, cargo=ClubeMembro.Cargo.BANIDO).select_related('usuario')
    
    form_convite = ConvidarUsuarioForm(clube=clube)

    contexto = {
        'clube': clube,
        'solicitacoes_pendentes': solicitacoes_pendentes,
        'moderadores': moderadores,
        'membros_comuns': membros_comuns,
        'membros_banidos': membros_banidos,
        'form_convite': form_convite
    }
    return render(request, 'principal/admin/gerenciar_membros.html', contexto)

@admin_clube_obrigatorio
def convidar_membro(request: HttpRequest, clube, **kwargs):
    if request.method == 'POST':
        form = ConvidarUsuarioForm(request.POST, clube=clube)
        if form.is_valid():
            usuario_a_convidar = form.cleaned_data['unique_id']  
            membro, created = ClubeMembro.all_objects.update_or_create(
                clube=clube,
                usuario=usuario_a_convidar,
                defaults={'deleted': None, 'cargo': ClubeMembro.Cargo.MEMBRO}
            )
            if created:
                messages.success(request, _("Usuário '%(nome_usuario)s' foi convidado e adicionado ao clube.") % {'nome_usuario': usuario_a_convidar.nome})
            else:
                messages.info(request, _("Usuário '%(nome_usuario)s' já estava no clube, mas foi restaurado.") % {'nome_usuario': usuario_a_convidar.nome})
        else:
            primeiro_erro = next(iter(form.errors.values()))[0]
            messages.error(request, primeiro_erro)
            
    return redirect('principal:gerenciar_membros', clube_id=clube.id)

@admin_clube_obrigatorio
def aprovar_membro(request: HttpRequest, clube, membro_id, **kwargs):
    if request.method == 'POST':
        membro = get_object_or_404(ClubeMembro, id=membro_id, clube=clube)
        if membro.cargo == ClubeMembro.Cargo.PENDENTE:
            membro.cargo = ClubeMembro.Cargo.MEMBRO
            membro.save()
            messages.success(request, _("Solicitação de '%(nome_usuario)s' aprovada.") % {'nome_usuario': membro.usuario.nome})
    return redirect('principal:gerenciar_membros', clube_id=clube.id)

@admin_clube_obrigatorio
def rejeitar_membro(request: HttpRequest, clube, membro_id, **kwargs):
    
    if request.method == 'POST':
        membro = get_object_or_404(ClubeMembro, id=membro_id, clube=clube)
        if membro.cargo == ClubeMembro.Cargo.PENDENTE:
            nome_usuario = membro.usuario.nome
            membro.delete()
            messages.info(request, _("Solicitação de '%(nome_usuario)s' rejeitada.") % {'nome_usuario': nome_usuario})
    return redirect('principal:gerenciar_membros', clube_id=clube.id)

@admin_clube_obrigatorio
def promover_membro(request: HttpRequest, clube, membro_id, **kwargs):
    """Promove um MEMBRO para MODERADOR."""
    if request.method == 'POST':
        membro = get_object_or_404(ClubeMembro, id=membro_id, clube=clube)
        if membro.cargo == ClubeMembro.Cargo.MEMBRO:
            membro.cargo = ClubeMembro.Cargo.MODERADOR
            membro.save()
            messages.success(request, _("'%(nome_usuario)s' foi promovido a moderador.") % {'nome_usuario': membro.usuario.nome})
    return redirect('principal:gerenciar_membros', clube_id=clube.id)

@admin_clube_obrigatorio
def rebaixar_membro(request: HttpRequest, clube, membro_id, **kwargs):
    """Rebaixa um MODERADOR para MEMBRO."""
    if request.method == 'POST':
        membro = get_object_or_404(ClubeMembro, id=membro_id, clube=clube)
        if membro.cargo == ClubeMembro.Cargo.MODERADOR:
            membro.cargo = ClubeMembro.Cargo.MEMBRO
            membro.save()
            messages.success(request, _("'%(nome_usuario)s' foi rebaixado para membro.") % {'nome_usuario': membro.usuario.nome})
    return redirect('principal:gerenciar_membros', clube_id=clube.id)

@admin_clube_obrigatorio
def remover_membro(request: HttpRequest, clube, membro_id, **kwargs):
    """Executa um soft delete no membro, removendo-o do clube."""
    if request.method == 'POST':
        membro = get_object_or_404(ClubeMembro, id=membro_id, clube=clube)
        if membro.cargo not in [ClubeMembro.Cargo.ADMIN, ClubeMembro.Cargo.BANIDO]:
            nome_usuario = membro.usuario.nome
            membro.delete()
            messages.info(request, _("'%(nome_usuario)s' foi removido do clube.") % {'nome_usuario': nome_usuario})
    return redirect('principal:gerenciar_membros', clube_id=clube.id)

@admin_clube_obrigatorio
def banir_membro(request: HttpRequest, clube, membro_id, **kwargs):
    if request.method == 'POST':
        membro = get_object_or_404(ClubeMembro, id=membro_id, clube=clube)
        if membro.cargo not in [ClubeMembro.Cargo.ADMIN, ClubeMembro.Cargo.BANIDO]:
            membro.cargo = ClubeMembro.Cargo.BANIDO
            membro.save()
            membro.delete()  
            messages.warning(
                request,
                _("'%(nome_usuario)s' foi BANIDO do clube.") % {'nome_usuario': membro.usuario.nome}
            )
    return redirect('principal:gerenciar_membros', clube_id=clube.id)

@admin_clube_obrigatorio
def desbanir_membro(request: HttpRequest, clube, membro_id, **kwargs):
    if request.method == 'POST':
        membro = get_object_or_404(ClubeMembro.all_objects, id=membro_id, clube=clube)
        
        if membro.cargo == ClubeMembro.Cargo.BANIDO:
            nome_usuario = membro.usuario.nome

            membro.undelete()
            membro.cargo = ClubeMembro.Cargo.PENDENTE  
            membro.save()
            
            messages.success(
                request,
                _("'%(nome_usuario)s' foi desbanido e pode solicitar a entrada no clube novamente.") % {'nome_usuario': nome_usuario}
            )
    
    return redirect('principal:gerenciar_membros', clube_id=clube.id)



@login_obrigatorio
def estante_pessoal(request):
    usuario = request.usuario_logado_obj

    estante_completa = EstantePessoal.objects.filter(usuario=usuario).select_related('livro', 'clube')

    livros_lendo = estante_completa.filter(status=EstantePessoal.StatusLeitura.LENDO)
    livros_lidos = estante_completa.filter(status=EstantePessoal.StatusLeitura.LIDO)
    livros_abandonados = estante_completa.filter(status=EstantePessoal.StatusLeitura.ABANDONADO)
    livros_favoritos = estante_completa.filter(favorito=True)

    contexto = {
        'usuario': usuario,
        'livros_lendo': livros_lendo,
        'livros_lidos': livros_lidos,
        'livros_abandonados': livros_abandonados,
        'livros_favoritos': livros_favoritos,
    }
    return render(request, 'principal/estante_pessoal.html', contexto)