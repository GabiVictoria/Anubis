from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpRequest
from django.contrib.auth.hashers import make_password, check_password
from django.contrib import messages
import re
from django.db import IntegrityError
from datetime import datetime, date
from django.utils import timezone
from .models import Usuario, generate_unique_id
from django.utils.translation import gettext as _ 
from inicial.models import Clube, ClubeMembro, LeituraClube 
from django.db.models import Q, Subquery, OuterRef, Count, CharField, Value
from .user_validator import send_validation_email, send_password_reset_email
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError

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
        
        try:
            validator = EmailValidator()
            validator(email) 
        except ValidationError:
            messages.error(request, _('Por favor, insira um endereço de e-mail válido.'))
            form_data_sem_email = form_data.copy()
            form_data_sem_email.pop('email_usuario', None)
            return render(request, 'inicial/cadastro.html', {'form_data': form_data_sem_email})

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
            # Cria o usuário mas com is_active=False
            novo_usuario = Usuario.objects.create(
                nome=nome, 
                email=email, 
                senha=senha_hashed, 
                data_nasc=data_nasc_str,
                is_active=False # O usuário começa inativo
            )
            
            # Envia o e-mail de validação
            if send_validation_email(request, novo_usuario):
                messages.success(request, _('Cadastro realizado com sucesso! Um e-mail de validação foi enviado para sua caixa de entrada.'))
                return redirect("inicial:login")
            else:
                # Se o e-mail falhar, podemos deletar o usuário ou permitir que ele peça um novo e-mail
                novo_usuario.delete() # Simples abordagem: deleta o usuário
                messages.error(request, _('Não foi possível enviar o e-mail de validação. Tente novamente mais tarde.'))
                return render(request, 'inicial/cadastro.html', {'form_data': form_data})

        except IntegrityError:
            messages.error(request, _('Este endereço de e-mail já está cadastrado. Por favor, utilize outro.'))
            form_data_sem_email = form_data.copy()
            form_data_sem_email.pop('email_usuario', None)
            return render(request, 'inicial/cadastro.html', {'form_data': form_data_sem_email})
        except Exception as e:
            print("-----------------------------------------")
            print(f"ERRO INESPERADO NA VIEW cadastrar_usuario: {e}")
            print(f"TIPO DO ERRO: {type(e)}")
            print("-----------------------------------------")
            
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
            
            if not usuario.is_active:
                send_validation_email(request, usuario) 
                messages.error(request, _("Sua conta ainda não foi ativada. Um novo e-mail de validação foi enviado para sua caixa de entrada. Por favor, verifique."))
                return render(request, 'inicial/login.html', {'form_data': form_data})

            if check_password(senha, usuario.senha):
  
                if not usuario.unique_id:
                    usuario.unique_id = generate_unique_id(prefix='@')
                    usuario.save()
            
                request.session['usuario_id'] = usuario.id
                request.session['usuario_nome'] = usuario.nome
                return redirect("principal:home") 
            else:
            
                messages.error(request, _("E-mail ou senha inválidos."))
                return render(request, 'inicial/login.html', {'form_data': form_data})

        except Usuario.DoesNotExist:
           
            messages.error(request, _("E-mail ou senha inválidos."))
            return render(request, 'inicial/login.html', {'form_data': form_data})
        
        except Exception as e:
            messages.error(request, _("Ocorreu um erro inesperado: %(error)s") % {'error': e})
            return render(request, 'inicial/login.html', {'form_data': form_data})

    return render(request, 'inicial/login.html')

def validate_email_view(request, token):
    """
    View para ativar a conta do usuário a partir do link no e-mail.
    """
    try:
        user = Usuario.objects.get(auth_token=token)
        user.is_active = True
        user.auth_token = "" # Limpa o token para não ser usado novamente
        user.save()
        messages.success(request, _('Seu e-mail foi validado com sucesso! Agora você pode fazer o login.'))
    except Usuario.DoesNotExist:
        messages.error(request, _('Token de validação inválido ou expirado.'))
    
    return redirect('inicial:login')

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
    message = messages.info(request, _("Entre ou cadastre-se para mais informações sobre os clubes"))
    return render(request, 'inicial/inicial_busca.html', contexto, message)


def request_password_reset(request):
    """
    Página onde o usuário insere o e-mail para pedir a recuperação.
    """
    if request.method == 'POST':
        email = request.POST.get('email_usuario')
        try:
            user = Usuario.objects.get(email=email)
            if send_password_reset_email(request, user):
                messages.success(request, _('Um e-mail com instruções para redefinir sua senha foi enviado.'))
                return redirect('inicial:login')
            else:
                messages.error(request, _('Não foi possível enviar o e-mail. Tente novamente mais tarde.'))
        except Usuario.DoesNotExist:
            # Não informe ao usuário se o e-mail existe ou não por segurança
            messages.success(request, _('Se este e-mail estiver cadastrado, um link de recuperação será enviado.'))
            return redirect('inicial:login')
            
    return render(request, 'inicial/reseta_senha.html')


def reset_password_view(request, token):
    """
    Página onde o usuário define a nova senha.
    """
    try:
        # Verifica se o token é válido e não expirou
        user = Usuario.objects.get(
            reset_token=token, 
            reset_token_expires__gt=timezone.now()
        )
    except Usuario.DoesNotExist:
        messages.error(request, _('O link para redefinição de senha é inválido ou já expirou.'))
        return redirect('inicial:request_password_reset')

    if request.method == 'POST':
        senha = request.POST.get('senha')
        confirma_senha = request.POST.get('confirma_senha')

        if senha != confirma_senha:
            messages.error(request, _('As senhas não coincidem.'))
            return render(request, 'inicial/form_senha.html', {'token': token})
        
        # Aqui você pode adicionar a mesma lógica de validação de força da senha do cadastro
        
        user.senha = make_password(senha)
        user.reset_token = "" # Limpa o token
        user.reset_token_expires = None
        user.save()
        
        messages.success(request, _('Sua senha foi redefinida com sucesso!'))
        return redirect('inicial:login')

    return render(request, 'inicial/form_senha.html', {'token': token})
