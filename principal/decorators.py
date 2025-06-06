
# considerar mudar depois para um arquivo utils.py no projeto
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from inicial.models import Usuario, ClubeMembro,Clube
from functools import wraps

def login_obrigatorio(view_func):
   
    # Decorator para views que exigem que o usuário esteja logado.
    # Redireciona para a página de login se o usuário não estiver autenticado
    # ou se a sessão for inválida.
   
    @wraps(view_func) # Preserva metadados da view original
    def _wrapped_view(request, *args, **kwargs):
        usuario_id = request.session.get('usuario_id')
        if usuario_id:
            try:
                usuario = Usuario.objects.get(id=usuario_id)
                request.usuario_logado_obj = usuario 
                return view_func(request, *args, **kwargs)
            except Usuario.DoesNotExist:
                request.session.flush()
                messages.error(request, "Por favor, faça login novamente.")
                return redirect('inicial:login')
        else:
            return redirect('inicial:login')
    return _wrapped_view


def admin_clube_obrigatorio(view_func):
    @login_obrigatorio # Primeiro garante que o usuário está logado
    @wraps(view_func) # É bom adicionar @wraps aqui também
    def _wrapped_view(request, clube_id, *args, **kwargs):
        clube_obj = get_object_or_404(Clube, id=clube_id) # Busquei e nomeei para clareza
        
        try:
            membro = ClubeMembro.objects.get(clube=clube_obj, usuario=request.usuario_logado_obj)
            if membro.cargo == ClubeMembro.Cargo.ADMIN:
                # CORREÇÃO AQUI: Passe o objeto 'clube_obj' para a view decorada.
                # A view decorada precisa aceitar este argumento.
                # Se a view espera 'clube', passe clube=clube_obj.
                # Se a view espera 'clube_obj' (como no meu exemplo anterior), passe clube_obj=clube_obj.
                # Vamos padronizar para passar como 'clube' para a view.
                kwargs['clube'] = clube_obj # Adiciona o objeto clube aos kwargs
                return view_func(request, clube_id, *args, **kwargs) # A view precisa ter 'clube' na sua assinatura
            else:
                messages.error(request, "Você não tem permissão de administrador para este clube.")
                return redirect('principal:detalhes_clube', clube_id=clube_id)
        except ClubeMembro.DoesNotExist:
            messages.error(request, "Você não é membro deste clube.")
            # Redirecionar para home pode ser melhor se ele não for membro e tentar acessar uma URL de admin
            return redirect('principal:home') 
    return _wrapped_view