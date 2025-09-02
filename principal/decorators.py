# anubis/principal/decorators.py

from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from inicial.models import Usuario, ClubeMembro, Clube
from functools import wraps

def login_obrigatorio(view_func):
    """
    Decorator para views que exigem que o usuário esteja logado.
    Redireciona para a página de login se o usuário não estiver autenticado.
    Este decorator está perfeito, não precisa de alterações.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        usuario_id = request.session.get('usuario_id')
        if usuario_id:
            try:
                usuario = Usuario.objects.get(id=usuario_id)
                request.usuario_logado_obj = usuario
                return view_func(request, *args, **kwargs)
            except Usuario.DoesNotExist:
                request.session.flush()
                messages.error(request, "Sessão inválida. Por favor, faça login novamente.")
                return redirect('inicial:login')
        else:
            messages.error(request, "Você precisa estar logado para acessar esta página.")
            return redirect('inicial:login')
    return _wrapped_view


def admin_clube_obrigatorio(view_func):
    """
    Decorator que verifica se um usuário está logado E se é admin do clube especificado.
    Ele busca o clube pelo 'clube_id' na URL e o injeta na view como um objeto 'clube'.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Passo 1: Verificar se o usuário está logado (lógica do primeiro decorator)
        if not hasattr(request, 'usuario_logado_obj'):
             # Se o decorator @login_obrigatorio não foi aplicado na view antes deste,
             # esta é uma salvaguarda.
             usuario_id = request.session.get('usuario_id')
             if not usuario_id:
                 messages.error(request, "Você precisa estar logado para acessar esta página.")
                 return redirect('inicial:login')
             try:
                 request.usuario_logado_obj = Usuario.objects.get(id=usuario_id)
             except Usuario.DoesNotExist:
                 messages.error(request, "Sessão inválida. Por favor, faça login novamente.")
                 return redirect('inicial:login')

        # Passo 2: Pegar o clube_id dos argumentos de keyword da URL (forma robusta)
        clube_pk = kwargs.get('clube_id')
        if clube_pk is None:
            raise TypeError("A view decorada com @admin_clube_obrigatorio precisa receber 'clube_id' da URL.")
            
        clube_obj = get_object_or_404(Clube, id=clube_pk)
        
        # Passo 3: Verificar a permissão de admin
        try:
            membro = ClubeMembro.objects.get(clube=clube_obj, usuario=request.usuario_logado_obj)
            if membro.cargo != ClubeMembro.Cargo.ADMIN:
                messages.error(request, "Você não tem permissão de administrador para acessar esta página.")
                return redirect('principal:detalhes_clube', clube_id=clube_pk)
        except ClubeMembro.DoesNotExist:
            messages.error(request, "Você não é membro deste clube e não pode acessar esta área.")
            return redirect('principal:detalhes_clube', clube_id=clube_pk)

        # Passo 4: Injetar o objeto 'clube' nos kwargs e chamar a view final
        kwargs['clube'] = clube_obj
        
        # A chamada final e correta, sem adicionar 'clube_id' posicionalmente
        return view_func(request, *args, **kwargs)
        
    return _wrapped_view