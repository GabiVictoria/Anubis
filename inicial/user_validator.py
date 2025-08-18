import uuid
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

def send_validation_email(request, user):
    """
    Gera um token de validação e envia o e-mail para o usuário.
    """
    # Gera um token único
    token = uuid.uuid4().hex
    user.auth_token = token
    user.save()

    # Monta a URL de validação
    validation_url = request.build_absolute_uri(f'/auth/validar_email/{token}/')

    # Renderiza o template de e-mail
    subject = 'Validação de Cadastro - Seu Clube do Livro'
    html_message = render_to_string('inicial/validation_email.html', {
        'user': user,
        'validation_url': validation_url
    })
    plain_message = strip_tags(html_message)
    from_email = settings.DEFAULT_FROM_EMAIL
    to = user.email

    try:
        send_mail(subject, plain_message, from_email, [to], html_message=html_message)
        return True
    except Exception as e:
        # Em um projeto real, você deveria logar este erro
        print(f"Erro ao enviar email de validação: {e}")
        return False


def send_password_reset_email(request, user):
    """
    Gera um token de redefinição de senha e envia o e-mail para o usuário.
    """
    # Gera um token único e define seu tempo de expiração (ex: 1 hora)
    token = uuid.uuid4().hex
    user.reset_token = token
    user.reset_token_expires = timezone.now() + timedelta(hours=1)
    user.save()

    # Monta a URL para redefinir a senha
    reset_url = request.build_absolute_uri(f'/auth/redefinir_senha/{token}/')

    # Renderiza o template de e-mail
    subject = 'Recuperação de Senha - Seu Clube do Livro'
    html_message = render_to_string('inicial/email_reseta_senha.html', {
        'user': user,
        'reset_url': reset_url
    })
    plain_message = strip_tags(html_message)
    from_email = settings.DEFAULT_FROM_EMAIL
    to = user.email

    try:
        send_mail(subject, plain_message, from_email, [to], html_message=html_message)
        return True
    except Exception as e:
        print(f"Erro ao enviar email de recuperação: {e}")
        return False