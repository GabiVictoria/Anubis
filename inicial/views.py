from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.http import HttpRequest
from django.contrib.auth.hashers import make_password, check_password #mecanismo para fazer hash na senha
from django.contrib import messages #para exibir mensagens de errro etc
import re #medir força de senha
from django.db import IntegrityError #para pegar e tratar exceções de integridade
from datetime import datetime, date
from . models import Usuario
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
        data_nasc = request.POST.get("data_nascimento")
        confirma_senha = request.POST.get("confirma_senha")

        form_data = {
            'nome_usuario': nome,
            'email_usuario': email,
            'data_nascimento': data_nasc,
            # para não perder todos os dados se der erro
        }

        if not all([nome, email, senha, confirma_senha, data_nasc]):
            messages.error(request, 'Todos os campos são obrigatórios.')
            return render(request, 'inicial/cadastro.html', {'form_data': form_data})
        
        data_nascimento_obj = datetime.strptime(data_nasc, '%Y-%m-%d').date()
        hoje = date.today()
        idade = hoje.year - data_nascimento_obj.year - \
                ((hoje.month, hoje.day) < (data_nascimento_obj.month, data_nascimento_obj.day))
        if idade < 13:
            messages.error(request, 'Você deve ter pelo menos 13 anos para se cadastrar.')
            return render(request, 'inicial/cadastro.html', {'form_data': form_data})


        if senha != confirma_senha:
            messages.error(request, 'As senhas não coincidem.')
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
                "A senha não atende aos critérios de segurança. "
                f"Ela deve conter: pelo menos {min_tamanho} caracteres, "
                "uma letra maiúscula (A-Z), uma letra minúscula (a-z), "
                "um número (0-9), e um caractere especial (ex: !@#$%&*)."
            )
            messages.error(request, requisitos_senha_texto)
            return render(request, 'inicial/cadastro.html', {'form_data': form_data})

        if Usuario.objects.filter(email=email).exists():
            messages.error(request, 'Este endereço de e-mail já está cadastrado.')
            form_data_sem_email = form_data.copy()
            form_data_sem_email.pop('email_usuario', None)
            return render(request, 'inicial/cadastro.html', {'form_data': form_data_sem_email})

        senha_hashed = make_password(senha)
        try:
            Usuario.objects.create(nome=nome, email=email, senha=senha_hashed, data_nasc=data_nasc)
            messages.success(request, 'Cadastro realizado com sucesso! Por favor, faça o login.')
            return redirect("inicial:login")
        except IntegrityError:
            messages.error(request, 'Este endereço de e-mail já está cadastrado. Por favor, utilize outro.')
            form_data_sem_email = form_data.copy()
            form_data_sem_email.pop('email_usuario', None)
            return render(request, 'inicial/cadastro.html', {'form_data': form_data_sem_email})
        except Exception as e:
            messages.error(request, f'Ocorreu um erro inesperado durante o cadastro. Tente novamente.')
            return render(request, 'inicial/cadastro.html', {'form_data': form_data})

    return render(request, 'inicial/cadastro.html')

def login(request:HttpRequest):
    if request.method == "POST":
        email = request.POST.get("email_usuario")
        senha = request.POST.get("senha_usuario")
        form_data = {"email_usuario" : email} 
        if not email or not senha:
            messages.error(request, "Todos os campos são obrigatórios.")
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
                messages.error(request, "E-mail ou senha inválidos.")
                return render(request, 'inicial/login.html', {'form_data': form_data})

        except Usuario.DoesNotExist:
            # Usuário não encontrado com o email fornecido
            messages.error(request, "E-mail ou senha inválidos.")
            return render(request, 'inicial/login.html', {'form_data': form_data})
        
        except Exception as e:
            # Trata outros erros inesperados
            messages.error(request, f"Ocorreu um erro inesperado: {e}")
            return render(request, 'inicial/login.html', {'form_data': form_data})

    return render(request, 'inicial/login.html')

def logout_usuario(request: HttpRequest):
    if request.session.items(): # Verifica se tem algo na sessão para limpar
        request.session.flush() # Limpa 
        messages.success(request, "Você foi desconectado com sucesso.")
    return redirect('inicial:login') 