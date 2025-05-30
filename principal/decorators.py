
# considerar mudar depois para um arquivo utils.py no projeto
from django.shortcuts import redirect
from django.contrib import messages
from inicial.models import Usuario 
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
