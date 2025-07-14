# anubis/principal/views.py com marcações de tradução

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponseForbidden, JsonResponse
from django.contrib import messages
from django.utils import timezone
from .decorators import login_obrigatorio, admin_clube_obrigatorio
from inicial.models import Clube, ClubeMembro, LeituraClube, Livro, Votacao, VotoUsuario, Mensagem, Usuario
from django.db import IntegrityError
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db.models import Q
from .forms import ClubeEditForm, DefinirLeituraAtualForm, CriarVotacaoForm
import os
import requests
import urllib.parse
from datetime import datetime
from django.utils.translation import gettext as _ 
from django.utils import formats

@login_obrigatorio
def home(request: HttpRequest):
    usuario_atual = request.usuario_logado_obj
    query = request.GET.get('q', None)

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
            'membros_count': clube.membros.count(),
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
    }
    return render(request, 'principal/home.html', contexto)

@login_obrigatorio
def criar_clube(request: HttpRequest):
    context_form_data = {
        'opcoes_privacidade': Clube.Privacidade.choices,
        'opcoes_limite_membros': Clube.LIMITE_MEMBROS_OPCOES,
    }

    if request.method == "POST":
        nome_clube = request.POST.get('nome_clube', '').strip()
        descricao_clube = request.POST.get('descricao_clube', '').strip()
        privacidade_clube_selecionada = request.POST.get('privacidade_clube')
        limite_membros_str_selecionado = request.POST.get('limite_membros')
        
        capa_clube_file = request.FILES.get('capa_clube')
        capa_recomendada_path_relativo = request.POST.get('capa_recomendada_selecionada')

        context_form_data.update({
            'nome_clube': nome_clube,
            'descricao_clube': descricao_clube,
            'privacidade_selecionada': privacidade_clube_selecionada,
            'limite_selecionado': limite_membros_str_selecionado,
        })

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
            novo_clube = Clube(
                nome=nome_clube,
                descricao=descricao_clube,
                privacidade=privacidade_clube_selecionada,
                limite_membros=limite_membros_int
            )

            if capa_clube_file:
                novo_clube.capa_clube = capa_clube_file
                novo_clube.capa_recomendada = None
            elif capa_recomendada_path_relativo:
                novo_clube.capa_recomendada = capa_recomendada_path_relativo
                novo_clube.capa_clube = None
            
            novo_clube.save()

            ClubeMembro.objects.create(
                usuario=usuario_criador,
                clube=novo_clube,
                cargo=ClubeMembro.Cargo.ADMIN
            )

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
        leituras_com_livro_buscado = LeituraClube.objects.filter(
            Q(livro__nome__icontains=query) &
            (Q(status=LeituraClube.StatusClube.LENDO_ATUALMENTE) | Q(status=LeituraClube.StatusClube.PROXIMO))
        ).select_related('clube', 'livro')

        clubes_encontrados_ids = set()

        def processar_clube(clube, razao_match):
            if clube.id not in clubes_encontrados_ids:
                clubes_encontrados_ids.add(clube.id)
                admin_membro = ClubeMembro.objects.filter(clube=clube, cargo=ClubeMembro.Cargo.ADMIN).order_by('data_inscricao').first()
                leitura_atual_obj = LeituraClube.objects.filter(clube=clube, status=LeituraClube.StatusClube.LENDO_ATUALMENTE).select_related('livro').first()
                
                resultados_finais.append({
                    'id': clube.id,
                    'nome': clube.nome,
                    'descricao': clube.descricao,
                    'capa_clube': clube.capa_clube,
                    'capa_recomendada': clube.capa_recomendada,
                    'fundador_nome': admin_membro.usuario.nome if admin_membro else _("N/D"),
                    'data_fundacao_formatada': clube.data_criacao.strftime("%B %Y") if clube.data_criacao else _("N/D"),
                    'membros_count': clube.membros.count(),
                    'leitura_atual_nome': leitura_atual_obj.livro.nome if leitura_atual_obj and leitura_atual_obj.livro else _("Nenhuma leitura atual"),
                    'match_reason': razao_match
                })

        for clube in clubes_por_nome:
            processar_clube(clube, _("Nome do clube corresponde a '%(query)s'") % {'query': query})

        for leitura in leituras_com_livro_buscado:
            processar_clube(leitura.clube, _("Livro '%(livro_nome)s' corresponde a '%(query)s'") % {'livro_nome': leitura.livro.nome, 'query': query})
    
    contexto = {
        'query': query,
        'resultados': resultados_finais,
        'nome_usuario': request.usuario_logado_obj.nome,
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

    admin_clube_obj = ClubeMembro.objects.filter(clube=clube, cargo=ClubeMembro.Cargo.ADMIN).order_by('data_inscricao').first()
    fundador_nome = admin_clube_obj.usuario.nome if admin_clube_obj else _("N/D")

    leitura_do_momento_obj = LeituraClube.objects.filter(
        clube=clube, 
        status=LeituraClube.StatusClube.LENDO_ATUALMENTE
    ).select_related('livro').first()

    votacao_ativa = Votacao.objects.filter(
        clube=clube, 
        data_fim__gte=timezone.now(), 
        is_ativa=True
    ).select_related('clube').prefetch_related('livros_opcoes').order_by('-data_inicio').first()
    
    opcoes_votacao_com_votos = []
    total_votos_na_votacao = 0
    usuario_ja_votou = False

    if votacao_ativa:
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
    
    mensagens_chat = []

    # --- CORREÇÃO APLICADA AQUI ---
    # Usa a função do Django que respeita o idioma ativo
    data_criacao_formatada = formats.date_format(clube.data_criacao, "F Y") if clube.data_criacao else ""
    data_fim_votacao_formatada = formats.date_format(votacao_ativa.data_fim, "d/m/Y H:i") if votacao_ativa else ""

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
        'nome_usuario': usuario_atual.nome,
        'default_avatar_url': staticfiles_storage.url('img/default_avatar.png'),
        'PrivacidadeChoices': Clube.Privacidade,
        'CargoChoices': ClubeMembro.Cargo,
        'data_criacao_formatada': data_criacao_formatada,
        'data_fim_votacao_formatada': data_fim_votacao_formatada,
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
        if clube.privacidade == Clube.Privacidade.PUBLICO:
            if not ClubeMembro.objects.filter(clube=clube, usuario=usuario).exists():
                if clube.membros.count() < clube.limite_membros:
                    ClubeMembro.objects.create(clube=clube, usuario=usuario, cargo=ClubeMembro.Cargo.MEMBRO)
                    messages.success(request, _("Você entrou no clube '%(nome_clube)s'!") % {'nome_clube': clube.nome})
                else:
                    messages.error(request, _("O clube '%(nome_clube)s' atingiu o limite de membros.") % {'nome_clube': clube.nome})
            else:
                messages.info(request, _("Você já é membro deste clube."))
        else:
            messages.error(request, _("Este clube é privado. A entrada precisa de aprovação."))
        return redirect('principal:detalhes_clube', clube_id=clube_id)
    return redirect('principal:detalhes_clube', clube_id=clube_id)

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
        return redirect('principal:detalhes_clube', clube_id=clube_id)
    return redirect('principal:detalhes_clube', clube_id=clube_id)
    
@admin_clube_obrigatorio
def editar_clube(request: HttpRequest, clube_id, clube, **kwargs):
    if request.method == 'POST':
        form = ClubeEditForm(request.POST, request.FILES, instance=clube)
        if form.is_valid():
            clube_editado = form.save(commit=False)

            capa_clube_file = request.FILES.get('capa_clube')
            capa_recomendada_path = request.POST.get('capa_recomendada_selecionada')

            if capa_clube_file:
                clube_editado.capa_clube = capa_clube_file
                clube_editado.capa_recomendada = None 
            elif capa_recomendada_path:
                clube_editado.capa_recomendada = capa_recomendada_path
                clube_editado.capa_clube.delete(save=False)
            
            clube_editado.save()
            messages.success(request, _("O clube '%(nome_clube)s' foi atualizado com sucesso!") % {'nome_clube': clube.nome})
            return redirect('principal:detalhes_clube', clube_id=clube.id)
        else:
            messages.error(request, _("Houve um erro no formulário. Por favor, verifique os dados."))
    else:
        form = ClubeEditForm(instance=clube)
    
    contexto = {
        'form': form,
        'clube': clube,
        'nome_usuario': request.usuario_logado_obj.nome,
    }
    return render(request, 'principal/admin/editar_clube.html', contexto)

@admin_clube_obrigatorio
def excluir_clube(request: HttpRequest, clube_id, clube, **kwargs):
    if request.method == 'POST':
        nome_clube = clube.nome
        clube.delete()
        messages.success(request, _("O clube '%(nome_clube)s' foi excluído permanentemente.") % {'nome_clube': nome_clube})
        return redirect('principal:home')
    else:
        messages.error(request, _("Ação inválida."))
        return redirect('principal:detalhes_clube', clube_id=clube_id)

@login_obrigatorio
def buscar_livros_api(request: HttpRequest):
    title_query = request.GET.get('title', '').strip()
    author_query = request.GET.get('author', '').strip()
    page = int(request.GET.get('page', '1'))

    if not title_query and not author_query:
        return JsonResponse({'error': _('Forneça um título ou autor para a busca.')}, status=400)

    livros_encontrados = {}
    google_total_items = 0

    # 1. Busca na API do Google Books
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
                        'paginas': volume_info.get('pageCount', None),
                        'capa': volume_info.get('imageLinks', {}).get('thumbnail', None)
                    }
    except requests.exceptions.RequestException as e:
        print(f"AVISO: Erro ao buscar no Google Books API: {e}")

    # 2. Busca na API da Open Library
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
                    'paginas': doc.get('number_of_pages_median', None),
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
def adicionar_livro_estante_clube(request: HttpRequest, clube_id, clube, **kwargs):
    contexto = {
        'clube': clube,
        'nome_usuario': request.usuario_logado_obj.nome,
    }
    return render(request, 'principal/admin/adicionar_livro_estante.html', contexto)

@admin_clube_obrigatorio
def adicionar_livro_api_para_estante(request: HttpRequest, clube_id, clube, **kwargs):
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
    
    return redirect('principal:adicionar_livro_estante_clube', clube_id=clube.id)

@admin_clube_obrigatorio
def definir_leitura_atual_clube(request: HttpRequest, clube_id, clube, **kwargs):
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
def criar_votacao_clube(request: HttpRequest, clube_id, clube, **kwargs):
    if request.method == 'POST':
        form = CriarVotacaoForm(request.POST, clube=clube)
        if form.is_valid():
            Votacao.objects.filter(clube=clube, is_ativa=True).update(is_ativa=False)

            nova_votacao = Votacao(
                clube=clube,
                data_fim=form.cleaned_data['data_fim'],
                is_ativa=True 
            )
            nova_votacao.save()
            nova_votacao.livros_opcoes.set(form.cleaned_data['livros_opcoes'])
            
            messages.success(request, _("Nova votação criada com sucesso!"))
            return redirect('principal:detalhes_clube', clube_id=clube.id)
        else:
            messages.error(request, _("Erro ao criar votação. Verifique os campos."))
    else:
        form = CriarVotacaoForm(clube=clube)
        
    contexto = {
        'clube': clube,
        'form': form,
        'nome_usuario': request.usuario_logado_obj.nome,
    }
    return render(request, 'principal/admin/criarvotacao.html', contexto)

def perfil(request): 
    return render(request, 'principal/perfil.html') 

def estante(request): 
    return render(request, 'principal/estante.html') 

def lidos_view(request):
    return render(request, 'principal/lidos.html') 

def abandonados_view(request):
    return render(request, 'principal/abandonados.html') 

def proximo_livro_view(request):
    return render(request, 'principal/proximo_livro.html')

def queremos_ler_view(request):
    return render(request, 'principal/queremos_ler.html')

def releitura_view(request):
    return render(request, 'principal/releitura.html')