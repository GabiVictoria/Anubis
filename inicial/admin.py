from django.contrib import admin

# Register your models here.
from .models import (
    Usuario, Livro, Clube, ClubeMembro, LeituraClube,
    Reuniao, EstantePessoal, Mensagem, Votacao, VotoUsuario
)

admin.site.register(Usuario)
admin.site.register(Livro)
admin.site.register(Clube)
admin.site.register(ClubeMembro)
admin.site.register(LeituraClube)
admin.site.register(Reuniao)
admin.site.register(EstantePessoal)
admin.site.register(Mensagem)
admin.site.register(Votacao)
admin.site.register(VotoUsuario)