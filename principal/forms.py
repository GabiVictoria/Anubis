# anubis/principal/forms.py
from django import forms
from inicial.models import Clube, Livro, LeituraClube, Votacao, ClubeMembro
from django.utils import timezone
from datetime import timedelta

class ClubeEditForm(forms.ModelForm):
    # Definimos explicitamente o widget para o campo da capa
    capa_clube = forms.ImageField(
        label="Nova Imagem de Capa (opcional)", 
        required=False, 
        widget=forms.FileInput  # <--- Esta é a mudança principal!
    )

    class Meta:
        model = Clube
        # O campo 'capa_clube' já foi definido acima, então podemos listá-lo aqui
        fields = ['nome', 'descricao', 'privacidade', 'limite_membros', 'capa_clube']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'privacidade': forms.RadioSelect,
        }
        labels = {
            'nome': 'Nome do Clube',
            'descricao': 'Descrição',
            'privacidade': 'Privacidade do Clube',
            'limite_membros': 'Limite Máximo de Membros',
        }

class AdicionarLivroEstanteForm(forms.Form):
    livro = forms.ModelChoiceField(
        queryset=Livro.objects.all().order_by('nome'), 
        label="Selecione o Livro",
        empty_label="--- Escolha um Livro ---"
    )
    status = forms.ChoiceField(
        choices=[ # Apenas opções relevantes para adicionar à estante
            (LeituraClube.StatusClube.A_LER, 'Quero Ler (Estante do Clube)'),
            (LeituraClube.StatusClube.PROXIMO, 'Próximo a Ser Lido pelo Clube'),
        ], 
        label="Status da Leitura no Clube"
    )

    def __init__(self, *args, clube=None, **kwargs):
        super().__init__(*args, **kwargs)
        if clube:
            # Excluir livros que já estão na estante do clube (qualquer status)
            livros_na_estante_ids = LeituraClube.objects.filter(clube=clube).values_list('livro_id', flat=True)
            self.fields['livro'].queryset = Livro.objects.exclude(id__in=livros_na_estante_ids).order_by('nome')


class DefinirLeituraAtualForm(forms.Form):
    leitura_clube_item = forms.ModelChoiceField(
        queryset=None, # Será definido na view
        label="Selecione o Livro da Estante para Ler Agora",
        empty_label="--- Escolha um Livro da Estante ---",
        widget=forms.RadioSelect # Para seleção única clara
    )

    def __init__(self, *args, clube=None, **kwargs):
        super().__init__(*args, **kwargs)
        if clube:
            # Livros que podem ser definidos como leitura atual (A_LER ou PROXIMO)
            self.fields['leitura_clube_item'].queryset = LeituraClube.objects.filter(
                clube=clube,
                status__in=[LeituraClube.StatusClube.A_LER, LeituraClube.StatusClube.PROXIMO]
            ).select_related('livro').order_by('livro__nome')
            self.fields['leitura_clube_item'].label_from_instance = lambda obj: f"{obj.livro.nome} (Status atual: {obj.get_status_display()})"


class CriarVotacaoForm(forms.Form):
    livros_opcoes = forms.ModelMultipleChoiceField(
        queryset=None, # Será definido na view
        widget=forms.CheckboxSelectMultiple,
        label="Selecione os Livros para a Votação (mínimo 2)"
    )
    # Adiciona um campo para o título da votação
    titulo_votacao = forms.CharField(
        label="Título da Votação (opcional)", 
        max_length=200, 
        required=False,
        help_text="Ex: Votação para livro de Julho"
    )
    data_fim = forms.DateTimeField(
        label="Data e Hora de Término da Votação",
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        initial=timezone.now() + timedelta(days=7) # Sugestão: 7 dias a partir de agora
    )

    def __init__(self, *args, clube=None, **kwargs):
        super().__init__(*args, **kwargs)
        if clube:
            # Opções de livros: aqueles na estante do clube como "A LER" ou "PROXIMO"
            self.fields['livros_opcoes'].queryset = Livro.objects.filter(
                leituraclube__clube=clube, 
                leituraclube__status__in=[LeituraClube.StatusClube.A_LER, LeituraClube.StatusClube.PROXIMO]
            ).distinct().order_by('nome')
    
    def clean_livros_opcoes(self):
        livros_selecionados = self.cleaned_data.get('livros_opcoes')
        if livros_selecionados and len(livros_selecionados) < 2:
            raise forms.ValidationError("Selecione pelo menos dois livros para a votação.")
        return livros_selecionados
