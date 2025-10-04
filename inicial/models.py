# inicial/models.py

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone 
from django.utils.translation import gettext_lazy as _ 
import random
import string

# --- E-X-P-L-I-C-A-Ç-Ã-O ---
# 1. Importamos as classes necessárias da biblioteca safedelete.
# SafeDeleteModel é a classe base que usaremos em vez de models.Model.
# SOFT_DELETE_CASCADE define que, ao deletar um objeto, seus dependentes também serão "soft deleted".
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE


def generate_unique_id(prefix, length=8):
    """Gera um ID aleatório único com um prefixo, garantindo que não exista no banco."""
    Model = Clube if prefix == '#' else Usuario
    while True:
        random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
        unique_id = f"{prefix}{random_part}"
        if not Model.all_objects.filter(unique_id=unique_id).exists(): # Usamos all_objects para garantir unicidade mesmo com deletados
            return unique_id
        
# ==============================================================================
# 1. MODELO DE USUÁRIO
# ==============================================================================
class Usuario(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    nome = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    senha = models.CharField(max_length=128)
    data_nasc = models.DateField()
    bio = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Bio"))
    foto_perfil = models.ImageField(upload_to='perfil/fotos/', null=True, blank=True, verbose_name=_("Foto de Perfil"))
    foto_capa = models.ImageField(upload_to='perfil/capas/', null=True, blank=True, verbose_name=_("Foto de Capa"))

    is_active = models.BooleanField(default=False)
    auth_token = models.CharField(max_length=100, blank=True)
    reset_token = models.CharField(max_length=100, blank=True)
    reset_token_expires = models.DateTimeField(null=True, blank=True)
    unique_id = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name=_("ID de Usuário"))

    def __str__(self):
        return self.email

# ==============================================================================
# 2. MODELO DE LIVRO
# ==============================================================================
class Livro(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    isbn13 = models.CharField(max_length=13, unique=True, null=True, blank=True)
    nome = models.CharField(max_length=200)
    autor = models.CharField(max_length=200)
    paginas = models.IntegerField(null=True, blank=True)
    data_publicacao = models.DateField(null=True, blank=True)
    capa = models.ImageField(upload_to='livros_capas/', null=True, blank=True)

    def __str__(self):
        return f"{self.nome} por {self.autor}"

# ==============================================================================
# 3. MODELO DE CLUBE E MEMBROS
# ==============================================================================
# O ClubeManager customizado e o campo 'is_active' foram removidos do Clube.
# A biblioteca safedelete já faz esse trabalho: por padrão, Clube.objects.all()
# retornará apenas os clubes não deletados. Para ver todos (incluindo os deletados), Clube.all_objects.all().

class Clube(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE
    
    class Privacidade(models.TextChoices):
        PUBLICO = 'PUBLICO', _('Público')
        PRIVADO = 'PRIVADO', _('Privado')

    LIMITE_MEMBROS_OPCOES = [
        (10, _('Até 10 membros')),
        (20, _('Até 20 membros')),
        (50, _('Até 50 membros')),
    ]

    nome = models.CharField(max_length=100)
    descricao = models.TextField(max_length=300)
    privacidade = models.CharField(
        max_length=10,
        choices=Privacidade.choices,
        default=Privacidade.PUBLICO
    )
    limite_membros = models.PositiveIntegerField(
        choices=LIMITE_MEMBROS_OPCOES,
        default=10
    )
    membros = models.ManyToManyField(
        Usuario,
        through='ClubeMembro',
        related_name='clubes_participados'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    capa_clube = models.ImageField(
        upload_to='clubes_capas/',
        null=True,
        blank=True
    )
    capa_recomendada = models.CharField(max_length=100, null=True, blank=True)
    unique_id = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name=_("ID do Clube"))

    def save(self, *args, **kwargs):
        if not self.pk and not self.unique_id:
            self.unique_id = generate_unique_id(prefix='#')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome

class ClubeMembro(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE
    
    class Cargo(models.TextChoices):
        ADMIN = 'ADMIN', _('Administrador')
        MODERADOR = 'MODERADOR', _('Moderador')
        MEMBRO = 'MEMBRO', _('Membro')
        PENDENTE = 'PENDENTE', _('Pendente')
        BANIDO = 'BANIDO', _('Banido')

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    clube = models.ForeignKey(Clube, on_delete=models.CASCADE)
    data_inscricao = models.DateTimeField(auto_now_add=True)
    cargo = models.CharField(max_length=10, choices=Cargo.choices, default=Cargo.MEMBRO)

    class Meta:
        unique_together = ('usuario', 'clube')

    def __str__(self):
        return f"{self.usuario.email} no clube {self.clube.nome} como {self.get_cargo_display()}"

# ==============================================================================
# 4. MODELOS DO SISTEMA DE VOTAÇÃO
# ==============================================================================
class Votacao(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE
    titulo = models.CharField(max_length=50)
    clube = models.ForeignKey(Clube, on_delete=models.CASCADE, related_name='votacoes')
    livros_opcoes = models.ManyToManyField(Livro)
    data_inicio = models.DateTimeField(auto_now_add=True)
    data_fim = models.DateTimeField()
    is_ativa = models.BooleanField(default=True)

    def __str__(self):
        return f"Votação para o clube '{self.clube.nome}' (termina em {self.data_fim.strftime('%d/%m/%Y')})"

class VotoUsuario(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE
    
    votacao = models.ForeignKey(Votacao, on_delete=models.CASCADE, related_name='votos')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    livro_votado = models.ForeignKey(Livro, on_delete=models.CASCADE)
    data_voto = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('votacao', 'usuario')

    def __str__(self):
        return f"Voto de {self.usuario.email} em '{self.livro_votado.nome}'"

# ==============================================================================
# 5. MODELO DA ESTANTE DO CLUBE
# ==============================================================================
class LeituraClube(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE
    
    class StatusClube(models.TextChoices):
        A_LER = 'A_LER', _('Queremos Ler')
        LENDO_ATUALMENTE = 'LENDO', _('Lendo Atualmente')
        FINALIZADO = 'FINALIZADO', _('Finalizado')
        ABANDONADO = 'ABANDONADO', _('Abandonado')

    clube = models.ForeignKey(Clube, on_delete=models.CASCADE)
    livro = models.ForeignKey(Livro, on_delete=models.CASCADE)
    status = models.CharField(max_length=15, choices=StatusClube.choices)
    nota_media_clube = models.DecimalField(
        max_digits=3, decimal_places=1, null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    data_finalizacao = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"'{self.livro.nome}' está como '{self.get_status_display()}' no clube '{self.clube.nome}'"

# ==============================================================================
# 6. MODELO DE REUNIÃO
# ==============================================================================
class Reuniao(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE
    
    class TipoReuniao(models.TextChoices):
        REMOTO = 'REMOTO', _('Remoto')
        PRESENCIAL = 'PRESENCIAL', _('Presencial')
        HIBRIDO = 'HIBRIDO', _('Híbrido')

    class TipoMeta(models.TextChoices):
        CAPITULOS = 'CAPITULOS', _('Capítulos')
        PAGINAS = 'PAGINAS', _('Páginas')

    clube = models.ForeignKey(Clube, on_delete=models.CASCADE, related_name='reunioes')
    leitura_associada = models.ForeignKey(LeituraClube, on_delete=models.SET_NULL, null=True, blank=True, related_name='reunioes_agendadas')
    titulo = models.CharField(max_length=200, default=_('Reunião de Discussão'))
    data_horario = models.DateTimeField()
    tipo = models.CharField(max_length=15, choices=TipoReuniao.choices, default=TipoReuniao.REMOTO)
    link_reuniao = models.URLField(max_length=500, null=True, blank=True)
    endereco = models.TextField(null=True, blank=True)
    descricao = models.TextField(null=True, blank=True, help_text=_("Detalhes, pauta ou o que será discutido na reunião."))
    
    meta_tipo = models.CharField(max_length=15, choices=TipoMeta.choices, null=True, blank=True)
    meta_quantidade = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.titulo} - {self.clube.nome}"

# ==============================================================================
# 7. MODELO DA ESTANTE PESSOAL
# ==============================================================================
class EstantePessoal(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    class StatusLeitura(models.TextChoices):
        LENDO = 'LENDO', _('Lendo')
        LIDO = 'LIDO', _('Lido')
        ABANDONADO = 'ABANDONADO', _('Abandonado')

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    livro = models.ForeignKey(Livro, on_delete=models.CASCADE)
    clube = models.ForeignKey(Clube, on_delete=models.CASCADE)
    status = models.CharField(max_length=15, choices=StatusLeitura.choices)
    nota_pessoal = models.DecimalField(
        max_digits=3, decimal_places=1, null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    favorito = models.BooleanField(default=False)
    data_modificacao = models.DateTimeField(auto_now=True)
    progresso_paginas = models.PositiveIntegerField(null=True, blank=True, default=0)

    class Meta:
        unique_together = ('usuario', 'livro', 'clube')

    def __str__(self):
        return f"Livro '{self.livro.nome}' na estante de {self.usuario.email} (Clube: {self.clube.nome})"

# ==============================================================================
# 8. MODELO DE MENSAGENS DO FÓRUM
# ==============================================================================
class Mensagem(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    clube = models.ForeignKey(Clube, on_delete=models.CASCADE)
    autor = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    texto = models.TextField()
    data_envio = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Mensagem de {self.autor.email} em '{self.clube.nome}'"
    

# ==============================================================================
# 9. MODELO DE AVALIAÇÃO DE LEITURA 
# ==============================================================================
class AvaliacaoLeitura(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    leitura_clube = models.ForeignKey(LeituraClube, on_delete=models.CASCADE, related_name='avaliacoes')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    nota = models.DecimalField(
        max_digits=3, decimal_places=1,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    data_avaliacao = models.DateTimeField(auto_now_add=True)

    class Meta:
       
        unique_together = ('leitura_clube', 'usuario')

    def __str__(self):
        return f"Nota {self.nota} de {self.usuario.nome} para '{self.leitura_clube.livro.nome}'"