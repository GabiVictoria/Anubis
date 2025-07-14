"""
WSGI config for anubis project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

# anubis/wsgi.py

import os
from django.core.wsgi import get_wsgi_application

# --- CORREÇÃO IMPORTANTE ---
# Importa o WhiteNoise para servir arquivos estáticos E de mídia
from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'anubis.settings')

# Pega a aplicação Django original
application = get_wsgi_application()

# Envolve a aplicação com o WhiteNoise, apontando para as pastas corretas
application = WhiteNoise(application, root=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'staticfiles'))
application.add_files(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'media'), prefix='media/')