from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.http import HttpRequest
from . models import Usuario
# Create your views here.

def inicial(request):
    contexto = {
        "nome":"Vick"
    }
    return render(request, 'inicial/home.html', contexto)

def cadastrar_usuario(request:HttpRequest):
    if request.method == "POST":
        nome = request.POST.get("nome_usuario")
        email = request.POST.get("email_usuario")
        senha = request.POST.get("senha_usuario")
        data_nasc = request.POST.get("data_nascimento")
        Usuario.objects.create(nome=nome, email=email, senha=senha, data_nasc=data_nasc)
        return redirect("inicial:login")
    return render(request, 'inicial/cadastro.html')


def login(request):
    #basicamente a variavel está recebendo todos os registros de usuarios
    usuarios = Usuario.objects.all()
    return render(request, 'inicial/login.html')