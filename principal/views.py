from django.shortcuts import render, redirect
from django.http import HttpRequest
from django.contrib import messages
from .decorators import login_obrigatorio
# Create your views here.

@login_obrigatorio
def home(request: HttpRequest):
    # A lógica de verificação de login e redirecionamento é tratada pelo decorator @login_obrigatorio.
    # podemos assumir que o usuário está logado. O objeto 'Usuario' correspondente ao usuário logado é anexado como 'request.usuario_logado_obj' pelo decorator e pode ser chamado para pegar infos.
    usuario_atual = request.usuario_logado_obj

    contexto = {
        "nome_usuario": usuario_atual.nome,
        "usuario_logado": True # Pode ser útil para condicionais no template(sem aplicação ainda)
    }
    return render(request, 'principal/home.html', contexto)