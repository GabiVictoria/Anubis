# anubis/principal/forms.py
from django import forms
from inicial.models import Clube, Livro, LeituraClube, Votacao, ClubeMembro, Reuniao
from django.utils import timezone
from datetime import timedelta
from django.utils.translation import gettext as _ 
from django.utils.safestring import mark_safe

class ClubeEditForm(forms.ModelForm):
   
    capa_clube = forms.ImageField(
        label="Nova Imagem de Capa (opcional)", 
        required=False, 
        widget=forms.FileInput   
    )

    class Meta:
        model = Clube
       
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
        queryset=None,
        widget=forms.CheckboxSelectMultiple,
      
        label=mark_safe(
            _('Selecione os Livros para a Votação') + 
            ' <span class="info-tooltip" data-tooltip="' + _('Selecione entre dois e três livros para a votação.') + '">'
            '<i class="fas fa-info-circle"></i>'
            '</span>'
        )
    )
    titulo_votacao = forms.CharField(
        label=_("Título da Votação"), 
        max_length=200, 
        required=True,
        help_text=_("Ex: Votação para livro de Julho")
    )
    data_fim = forms.DateTimeField(
        label=_("Data e Hora de Término da Votação"),
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        required=True,
        initial=timezone.now() + timedelta(days=7)
    )

    def __init__(self, *args, clube=None, **kwargs):
        super().__init__(*args, **kwargs)
        if clube:
            self.fields['livros_opcoes'].queryset = Livro.objects.filter(
                leituraclube__clube=clube, 
                leituraclube__status__in=[LeituraClube.StatusClube.A_LER, LeituraClube.StatusClube.PROXIMO]
            ).distinct().order_by('nome')
    
    def clean_livros_opcoes(self):
        livros_selecionados = self.cleaned_data.get('livros_opcoes')
        if livros_selecionados and len(livros_selecionados) < 2:
            raise forms.ValidationError(_("Selecione pelo menos dois livros para a votação."))
        return livros_selecionados

    def clean_data_fim(self):
        data_fim_inserida = self.cleaned_data.get('data_fim')
        if data_fim_inserida:
            agora = timezone.now()
            tempo_minimo_permitido = agora + timedelta(hours=1)
            if data_fim_inserida < tempo_minimo_permitido:
                raise forms.ValidationError(
                    _("A votação deve durar pelo menos 1 hora. Por favor, escolha um horário futuro.")
                )
        return data_fim_inserida
class DateTimePickerInput(forms.DateTimeInput):
    input_type = 'datetime-local'
    
class ReuniaoForm(forms.ModelForm):
    """Formulário para criar e editar uma Reunião."""
    class Meta:
        model = Reuniao
        fields = [
            'titulo', 'leitura_associada', 'data_horario', 'tipo', 
            'link_reuniao', 'endereco', 'descricao', 
            'meta_tipo', 'meta_quantidade'
        ]
        widgets = {
            'data_horario': DateTimePickerInput(),
        }

    def __init__(self, *args, **kwargs):
        clube = kwargs.pop('clube', None)
        super().__init__(*args, **kwargs)
        if clube:
            
            self.fields['leitura_associada'].queryset = LeituraClube.objects.filter(clube=clube)
        
       
        self.fields['meta_quantidade'].widget.attrs.update({'placeholder': _('Ex: 50 ou 5')})
        self.fields['link_reuniao'].widget.attrs.update({'placeholder': 'https://...'})
        self.fields['endereco'].widget.attrs.update({'placeholder': _('Ex: Rua Fictícia, 123, Bairro')})
        self.fields['leitura_associada'].label = _("Livro em Discussão (opcional)")
        self.fields['meta_tipo'].label = _("Tipo de Meta (opcional)")
        self.fields['meta_quantidade'].label = _("Quantidade da Meta (opcional)")

   
    def clean_data_horario(self):
        data_horario_inserida = self.cleaned_data.get('data_horario')
        if data_horario_inserida:
            agora = timezone.now()
            tempo_minimo_permitido = agora + timedelta(hours=4)
            if data_horario_inserida < tempo_minimo_permitido:
                raise forms.ValidationError(
                    _("A reunião deve ser agendada com pelo menos 4 horas de antecedência.")
                )
        return data_horario_inserida

    
    def clean(self):
        cleaned_data = super().clean()
        
        tipo_reuniao = cleaned_data.get('tipo')
        link_reuniao = cleaned_data.get('link_reuniao')
        endereco = cleaned_data.get('endereco')

      
        if tipo_reuniao == Reuniao.TipoReuniao.REMOTO and not link_reuniao:
           
            self.add_error('link_reuniao', _("Para reuniões remotas, o link da reunião é obrigatório."))

      
        if tipo_reuniao == Reuniao.TipoReuniao.PRESENCIAL and not endereco:
            
            self.add_error('endereco', _("Para reuniões presenciais, o endereço é obrigatório."))

   
        if tipo_reuniao == Reuniao.TipoReuniao.HIBRIDO:
            if not link_reuniao:
                self.add_error('link_reuniao', _("Para reuniões híbridas, o link da reunião é obrigatório."))
            if not endereco:
                self.add_error('endereco', _("Para reuniões híbridas, o endereço é obrigatório."))
                
        return cleaned_data
    
class VotacaoEditForm(forms.ModelForm):
    """Formulário para editar uma Votação existente."""
    class Meta:
        model = Votacao
        fields = ['data_fim', 'livros_opcoes']
        widgets = {
            'data_fim': DateTimePickerInput(),
            'livros_opcoes': forms.CheckboxSelectMultiple
        }

    def __init__(self, *args, **kwargs):
        clube = kwargs.pop('clube', None)
        super().__init__(*args, **kwargs)
        if clube:
            # Mostra apenas os livros elegíveis do clube como opções
            livros_elegiveis = LeituraClube.objects.filter(
                clube=clube, 
                status__in=[LeituraClube.StatusClube.A_LER, LeituraClube.StatusClube.PROXIMO]
            ).values_list('livro__id', flat=True)
            self.fields['livros_opcoes'].queryset = Livro.objects.filter(id__in=livros_elegiveis)