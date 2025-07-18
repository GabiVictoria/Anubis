from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpRequest
from django.contrib.auth.hashers import make_password, check_password
from django.contrib import messages
import re
from django.db import IntegrityError
from datetime import datetime, date
from .models import Usuario
from django.utils.translation import gettext as _ 
from inicial.models import Clube, ClubeMembro, LeituraClube 
from django.db.models import Q, Subquery, OuterRef, Count, CharField, Value

# Create your views here.

def root_dispatch_view(request: HttpRequest):
    # Redireciona o usuário com base na sessão.
    if request.session.get('usuario_id'):
        # Usuário está logado, redireciona para a página principal da aplicação para logados.
        return redirect('principal:home')
    else:
        # Usuário não está logado
        return redirect('inicial:inicial')

def inicial(request):
    return render(request, 'inicial/inicial.html')

def cadastrar_usuario(request:HttpRequest):
    if request.method == "POST":
        nome = request.POST.get("nome_usuario")
        email = request.POST.get("email_usuario")
        senha = request.POST.get("senha_usuario")
        data_nasc_str = request.POST.get("data_nascimento")
        confirma_senha = request.POST.get("confirma_senha")

        form_data = {
            'nome_usuario': nome,
            'email_usuario': email,
            'data_nascimento': data_nasc_str,
            # para não perder todos os dados se der erro
        }

        if not all([nome, email, senha, confirma_senha, data_nasc_str]):
            messages.error(request, _('Todos os campos são obrigatórios.'))
            return render(request, 'inicial/cadastro.html', {'form_data': form_data})
        
        data_nascimento_obj = datetime.strptime(data_nasc_str, '%Y-%m-%d').date()
        hoje = date.today()
        idade = hoje.year - data_nascimento_obj.year - \
                ((hoje.month, hoje.day) < (data_nascimento_obj.month, data_nascimento_obj.day))
        if idade < 13:
            messages.error(request, _('Você deve ter pelo menos 13 anos para se cadastrar.'))
            return render(request, 'inicial/cadastro.html', {'form_data': form_data})

        if senha != confirma_senha:
            messages.error(request, _('As senhas não coincidem.'))
            return render(request, 'inicial/cadastro.html', {'form_data': form_data})
        
        is_strong_password = True 
        min_tamanho = 6
        has_uppercase = re.search(r"[A-Z]", senha)
        has_lowercase = re.search(r"[a-z]", senha)
        has_digit = re.search(r"[0-9]", senha)
        has_special = re.search(r"[!@#$%^&*(),.?\":{}|<>]", senha)
        if len(senha) < min_tamanho or not has_uppercase or not has_lowercase or not has_digit or not has_special:
            is_strong_password = False
        if not is_strong_password:
            requisitos_senha_texto = (
                _("A senha não atende aos critérios de segurança. ") +
                _("Ela deve conter: pelo menos %(min_tamanho)s caracteres, ") % {'min_tamanho': min_tamanho} +
                _("uma letra maiúscula (A-Z), uma letra minúscula (a-z), ") +
                _("um número (0-9), e um caractere especial (ex: !@#$%&*).")
            )
            messages.error(request, requisitos_senha_texto)
            return render(request, 'inicial/cadastro.html', {'form_data': form_data})

        if Usuario.objects.filter(email=email).exists():
            messages.error(request, _('Este endereço de e-mail já está cadastrado.'))
            form_data_sem_email = form_data.copy()
            form_data_sem_email.pop('email_usuario', None)
            return render(request, 'inicial/cadastro.html', {'form_data': form_data_sem_email})

        senha_hashed = make_password(senha)
        try:
            Usuario.objects.create(nome=nome, email=email, senha=senha_hashed, data_nasc=data_nasc_str) # Corrigido para salvar a string
            messages.success(request, _('Cadastro realizado com sucesso! Por favor, faça o login.'))
            return redirect("inicial:login")
        except IntegrityError:
            messages.error(request, _('Este endereço de e-mail já está cadastrado. Por favor, utilize outro.'))
            form_data_sem_email = form_data.copy()
            form_data_sem_email.pop('email_usuario', None)
            return render(request, 'inicial/cadastro.html', {'form_data': form_data_sem_email})
        except Exception as e:
            messages.error(request, _('Ocorreu um erro inesperado durante o cadastro. Tente novamente.'))
            return render(request, 'inicial/cadastro.html', {'form_data': form_data})

    return render(request, 'inicial/cadastro.html')

def login(request:HttpRequest):
    if request.method == "POST":
        email = request.POST.get("email_usuario")
        senha = request.POST.get("senha_usuario")
        form_data = {"email_usuario" : email} 
        if not email or not senha:
            messages.error(request, _("Todos os campos são obrigatórios."))
            return render(request, 'inicial/login.html', {'form_data': form_data})
        try:        
            usuario = Usuario.objects.get(email=email)
            if check_password(senha, usuario.senha):
                # Senha correta - config da sessão
                request.session['usuario_id'] = usuario.id
                request.session['usuario_nome'] = usuario.nome
                return redirect("principal:home") 
            else:
                # Senha incorreta
                messages.error(request, _("E-mail ou senha inválidos."))
                return render(request, 'inicial/login.html', {'form_data': form_data})

        except Usuario.DoesNotExist:
            # Usuário não encontrado com o email fornecido
            messages.error(request, _("E-mail ou senha inválidos."))
            return render(request, 'inicial/login.html', {'form_data': form_data})
        
        except Exception as e:
            # Trata outros erros inesperados
            messages.error(request, _("Ocorreu um erro inesperado: %(error)s") % {'error': e})
            return render(request, 'inicial/login.html', {'form_data': form_data})

    return render(request, 'inicial/login.html')

def logout_usuario(request: HttpRequest):
    if request.session.items(): # Verifica se tem algo na sessão para limpar
        request.session.flush() # Limpa 
        messages.success(request, _("Você foi desconectado com sucesso."))
    return redirect('inicial:login') 


def inicial_busca_view(request):
  
    query = request.GET.get('q', '').strip()
    resultados_finais = []

    if query:
       
        criador_subquery = ClubeMembro.objects.filter(
            clube=OuterRef('pk'), 
            cargo=ClubeMembro.Cargo.ADMIN
        ).order_by('data_inscricao').values('usuario__nome')[:1]

        
        livro_atual_subquery = LeituraClube.objects.filter(
            clube=OuterRef('pk'),
            status=LeituraClube.StatusClube.LENDO_ATUALMENTE
        ).values('livro__nome')[:1]

       
        clubes_por_nome = Clube.objects.filter(nome__icontains=query)

      
        clubes_por_livro = Clube.objects.filter(
            leituraclube__livro__nome__icontains=query,
            leituraclube__status__in=[
                LeituraClube.StatusClube.LENDO_ATUALMENTE,
                LeituraClube.StatusClube.PROXIMO
            ]
        )

        
        todos_os_clubes_encontrados = (clubes_por_nome | clubes_por_livro).distinct()

       
        resultados_finais = todos_os_clubes_encontrados.annotate(
            membros_count=Count('membros'),
            criado_por=Subquery(criador_subquery, output_field=CharField()),
            livro_atual=Subquery(livro_atual_subquery, output_field=CharField())
        )

    contexto = {
        'query': query,
        'resultados': resultados_finais,
    }

    return render(request, 'inicial/inicial_busca.html', contexto)
