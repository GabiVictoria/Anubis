
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone # para manipulação de data/hora

# ==============================================================================
# 1. MODELO DE USUÁRIO
# ==============================================================================
class Usuario(models.Model):
    nome = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    senha = models.CharField(max_length=128)
    data_nasc = models.DateField()

    def __str__(self):
        return self.email

# ==============================================================================
# 2. MODELO DE LIVRO
# ==============================================================================
class Livro(models.Model):
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
class Clube(models.Model):
    class Privacidade(models.TextChoices):
        PUBLICO = 'PUBLICO', 'Público'
        PRIVADO = 'PRIVADO', 'Privado'
    LIMITE_MEMBROS_OPCOES = [
        (10, 'Até 10 membros'),
        (20, 'Até 20 membros'),
        (50, 'Até 50 membros'),
    ]

    nome = models.CharField(max_length=100)
    descricao = models.TextField()
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
    
    # NOVO CAMPO: Data de Criação
    data_criacao = models.DateTimeField(auto_now_add=True)

    # NOVO CAMPO: Capa do Clube
    capa_clube = models.ImageField(
        upload_to='clubes_capas/', # Define o subdiretório dentro de MEDIA_ROOT
        null=True,                 # Permite que o campo seja nulo no banco de dados
        blank=True                 # Permite que o campo seja vazio em formulários
    )

    def __str__(self):
        return self.nome

class ClubeMembro(models.Model):
    class Cargo(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        MODERADOR = 'MODERADOR', 'Moderador'
        MEMBRO = 'MEMBRO', 'Membro'

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    clube = models.ForeignKey(Clube, on_delete=models.CASCADE)
    data_inscricao = models.DateTimeField(auto_now_add=True)
    cargo = models.CharField(max_length=10, choices=Cargo.choices, default=Cargo.MEMBRO)

    class Meta:
        unique_together = ('usuario', 'clube')

    def __str__(self):
        return f"{self.usuario.email} no clube {self.clube.nome} como {self.get_cargo_display()}"


# MUDANÇA: Novos modelos para o sistema de votação.
# ==============================================================================
# 4. MODELOS DO SISTEMA DE VOTAÇÃO
# ==============================================================================
class Votacao(models.Model):
    """
    Representa uma sessão de votação para escolher o próximo livro de um clube.
    """
    clube = models.ForeignKey(Clube, on_delete=models.CASCADE, related_name='votacoes')
    livros_opcoes = models.ManyToManyField(Livro)
    data_inicio = models.DateTimeField(auto_now_add=True)
    data_fim = models.DateTimeField()
    is_ativa = models.BooleanField(default=True)

    def __str__(self):
        return f"Votação para o clube '{self.clube.nome}' (termina em {self.data_fim.strftime('%d/%m/%Y')})"

class VotoUsuario(models.Model):
    """
    Registra o voto de um usuário em um livro dentro de uma votação específica.
    """
    votacao = models.ForeignKey(Votacao, on_delete=models.CASCADE, related_name='votos')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    livro_votado = models.ForeignKey(Livro, on_delete=models.CASCADE)
    data_voto = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Garante que um usuário só pode votar uma vez por votação.
        unique_together = ('votacao', 'usuario')

    def __str__(self):
        return f"Voto de {self.usuario.email} em '{self.livro_votado.nome}'"


# Os modelos abaixo foram renumerados.
# ==============================================================================
# 5. MODELO DA ESTANTE DO CLUBE
# ==============================================================================
class LeituraClube(models.Model):
    class StatusClube(models.TextChoices):
        A_LER = 'A_LER', 'A Ler (Lista de Desejos)'
        PROXIMO = 'PROXIMO', 'Próximo a Ser Lido'
        LENDO_ATUALMENTE = 'LENDO', 'Lendo Atualmente'
        FINALIZADO = 'FINALIZADO', 'Finalizado'

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
class Reuniao(models.Model):
    class TipoReuniao(models.TextChoices):
        REMOTO = 'REMOTO', 'Remoto'
        PRESENCIAL = 'PRESENCIAL', 'Presencial'

    class TipoMeta(models.TextChoices):
        CAPITULOS = 'CAPITULOS', 'Capítulos'
        PAGINAS = 'PAGINAS', 'Páginas'

    leitura_clube = models.ForeignKey(LeituraClube, on_delete=models.CASCADE, related_name='reunioes')
    titulo = models.CharField(max_length=200, default='Reunião de Discussão')
    data_horario = models.DateTimeField()
    tipo = models.CharField(max_length=15, choices=TipoReuniao.choices, default=TipoReuniao.REMOTO)
    link_reuniao = models.URLField(max_length=500, null=True, blank=True)
    endereco = models.TextField(null=True, blank=True)
    meta_tipo = models.CharField(max_length=15, choices=TipoMeta.choices, null=True, blank=True)
    meta_quantidade = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.titulo} - {self.leitura_clube.clube.nome}"

# ==============================================================================
# 7. MODELO DA ESTANTE PESSOAL
# ==============================================================================
class EstantePessoal(models.Model):
    class StatusLeitura(models.TextChoices):
        LENDO = 'LENDO', 'Lendo'
        LIDO = 'LIDO', 'Lido'
        ABANDONADO = 'ABANDONADO', 'Abandonado'

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
class Mensagem(models.Model):
    clube = models.ForeignKey(Clube, on_delete=models.CASCADE)
    autor = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    texto = models.TextField()
    data_envio = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Mensagem de {self.autor.email} em '{self.clube.nome}'"