# anubis/principal/forms.py
from django import forms
from inicial.models import Clube, Livro, LeituraClube, Votacao, ClubeMembro, Reuniao, Usuario
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
            'descricao': forms.Textarea(attrs={'rows': 3, 'maxlength': 300, 'minlength': 50, 'placeholder': _('min 50 caracteres e max 300')}),
            'nome':  forms.Textarea(attrs={'rows': 3, 'maxlength': 100, 'minlength': 40}),
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
        choices=[
            (LeituraClube.StatusClube.A_LER, 'Quero Ler (Estante do Clube)'),
            
        ], 
        label="Status da Leitura no Clube"
    )

    def __init__(self, *args, clube=None, **kwargs):
        super().__init__(*args, **kwargs)
        if clube:
            livros_na_estante_ids = LeituraClube.objects.filter(clube=clube).values_list('livro_id', flat=True)
            self.fields['livro'].queryset = Livro.objects.exclude(id__in=livros_na_estante_ids).order_by('nome')


class DefinirLeituraAtualForm(forms.Form):
    leitura_clube_item = forms.ModelChoiceField(
        queryset=None,
        label="Selecione o Livro da Estante para Ler Agora",
        empty_label="--- Escolha um Livro da Estante ---",
        widget=forms.RadioSelect
    )

    def __init__(self, *args, clube=None, **kwargs):
        super().__init__(*args, **kwargs)
        if clube:
            self.fields['leitura_clube_item'].queryset = LeituraClube.objects.filter(
                clube=clube,
                status__in=[LeituraClube.StatusClube.A_LER, LeituraClube.StatusClube.ABANDONADO]
            ).select_related('livro').order_by('livro__nome')
            self.fields['leitura_clube_item'].label_from_instance = lambda obj: f"{obj.livro.nome} (Status atual: {obj.get_status_display()})"




class CriarVotacaoForm(forms.ModelForm):
    livro_opcao_1 = forms.ModelChoiceField(
        queryset=None,
        label=_("Opção de Livro 1"),
        required=True,
        empty_label=_("--- Selecione o primeiro livro ---")
    )
    livro_opcao_2 = forms.ModelChoiceField(
        queryset=None,
        label=_("Opção de Livro 2"),
        required=True,
        empty_label=_("--- Selecione o segundo livro ---")
    )
    livro_opcao_3 = forms.ModelChoiceField(
        queryset=None,
        label=_("Opção de Livro 3 (Opcional)"),
        required=False,
        empty_label=_("--- Selecione o terceiro livro ---")
    )

    class Meta:
        model = Votacao
        fields = ['titulo', 'data_fim']
        labels = {
            'titulo': _("Título da Votação"),
            'data_fim': _("Data e Hora de Término"),
        }
        widgets = {
            'data_fim': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
        help_texts = {
            'titulo': _("Ex: Votação para livro de Julho"),
        }

    def __init__(self, *args, **kwargs):
        clube = kwargs.pop('clube', None)
        super().__init__(*args, **kwargs)
        if clube:
            livros_elegiveis = Livro.objects.filter(
                leituraclube__clube=clube,
                leituraclube__status__in=[
                    LeituraClube.StatusClube.A_LER,
                    LeituraClube.StatusClube.PROXIMO
                ]
            ).distinct().order_by('nome')
            self.fields['livro_opcao_1'].queryset = livros_elegiveis
            self.fields['livro_opcao_2'].queryset = livros_elegiveis
            self.fields['livro_opcao_3'].queryset = livros_elegiveis

    def clean(self):
        cleaned_data = super().clean()
        data_fim = cleaned_data.get("data_fim")

        # ✅ Validação: duração mínima de 1h
        if data_fim and data_fim < timezone.now() + timedelta(hours=1):
            raise forms.ValidationError(
                _("A votação deve durar pelo menos 1 hora a partir de agora.")
            )

        livros = [
            cleaned_data.get('livro_opcao_1'),
            cleaned_data.get('livro_opcao_2'),
            cleaned_data.get('livro_opcao_3')
        ]
        livros_selecionados = [livro for livro in livros if livro is not None]

        if len(livros_selecionados) != len(set(livros_selecionados)):
            raise forms.ValidationError(
                _("Você não pode selecionar o mesmo livro mais de uma vez. Por favor, escolha livros diferentes.")
            )

        if len(livros_selecionados) < 2:
            raise forms.ValidationError(
                _("Por favor, selecione pelo menos dois livros para a votação.")
            )

        self.cleaned_data['livros_opcoes'] = livros_selecionados
        return cleaned_data


class VotacaoEditForm(forms.ModelForm):
  
    
    class Meta:
        model = Votacao
        fields = ['titulo', 'data_fim']
        widgets = {
            'data_fim': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
        labels = {
            'titulo': _("Título da Votação"),
            'data_fim': _("Nova Data e Hora de Término"),
        }

    def __init__(self, *args, **kwargs):
        
        kwargs.pop('clube', None)
        super().__init__(*args, **kwargs)

    def clean_data_fim(self):
       
        nova_data_fim = self.cleaned_data.get('data_fim')
        
        if self.instance and nova_data_fim:
            data_original = self.instance.data_fim
            
            if nova_data_fim <= data_original:
                raise forms.ValidationError(
                    _("A nova data de término deve ser posterior à data atual (%s).") % data_original.strftime('%d/%m/%Y %H:%M')
                )
        
        return nova_data_fim

class DateTimePickerInput(forms.DateTimeInput):
    input_type = 'datetime-local'
    
class ReuniaoForm(forms.ModelForm):
    class Meta:
        model = Reuniao
        fields = ['titulo', 'leitura_associada', 'data_horario', 'tipo', 'link_reuniao', 'endereco', 'descricao', 'meta_tipo', 'meta_quantidade']
        widgets = {'data_horario': DateTimePickerInput()}
        labels = {
            'leitura_associada': _("Livro em Discussão (opcional)"),
            'meta_tipo': _("Tipo de Meta (opcional)"),
            'meta_quantidade': _("Quantidade da Meta (opcional)"),
        }

    def __init__(self, *args, **kwargs):
        clube = kwargs.pop('clube', None)
        super().__init__(*args, **kwargs)
        if clube:
            self.fields['leitura_associada'].queryset = LeituraClube.objects.filter(clube=clube)
        self.fields['meta_quantidade'].widget.attrs.update({'placeholder': _('Ex: 50 ou 5')})
        self.fields['link_reuniao'].widget.attrs.update({'placeholder': 'https://...'})
        self.fields['endereco'].widget.attrs.update({'placeholder': _('Ex: Rua Fictícia, 123, Bairro')})

    def clean_data_horario(self):
        data_horario_inserida = self.cleaned_data.get('data_horario')
        if data_horario_inserida and data_horario_inserida < timezone.now() + timedelta(hours=4):
            raise forms.ValidationError(_("A reunião deve ser agendada com pelo menos 4 horas de antecedência."))
        return data_horario_inserida

    def clean(self):
        cleaned_data = super().clean()
        tipo_reuniao = cleaned_data.get('tipo')
        if tipo_reuniao == Reuniao.TipoReuniao.REMOTO and not cleaned_data.get('link_reuniao'):
            self.add_error('link_reuniao', _("Para reuniões remotas, o link é obrigatório."))
        if tipo_reuniao == Reuniao.TipoReuniao.PRESENCIAL and not cleaned_data.get('endereco'):
            self.add_error('endereco', _("Para reuniões presenciais, o endereço é obrigatório."))
        if tipo_reuniao == Reuniao.TipoReuniao.HIBRIDO and not (cleaned_data.get('link_reuniao') and cleaned_data.get('endereco')):
            self.add_error(None, _("Para reuniões híbridas, tanto o link quanto o endereço são obrigatórios."))
        return cleaned_data
    
class ConvidarUsuarioForm(forms.Form):
    unique_id = forms.CharField(
        label=_("ID do Usuário para Convidar"),
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': '@exemplo123'})
    )

    def __init__(self, *args, **kwargs):
        self.clube = kwargs.pop('clube', None)
        super().__init__(*args, **kwargs)

    def clean_unique_id(self):
        uid = self.cleaned_data.get('unique_id')
        if not uid or not uid.startswith('@'):
            raise forms.ValidationError(_("O ID do usuário deve começar com '@'."))
        
        try:
            usuario = Usuario.objects.get(unique_id=uid)
        except Usuario.DoesNotExist:
            raise forms.ValidationError(_("Nenhum usuário encontrado com este ID."))

        membro_existente = ClubeMembro.objects.filter(clube=self.clube, usuario=usuario).first()
        if membro_existente:
            if membro_existente.cargo == ClubeMembro.Cargo.BANIDO:
                raise forms.ValidationError(_("Este usuário está banido deste clube e não pode ser convidado."))
            else:
                raise forms.ValidationError(_("Este usuário já é membro ou tem uma solicitação pendente para este clube."))
        return usuario
    
class PerfilEditForm(forms.ModelForm):
    bio = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 1, 'maxlength': 100,'minlength': 10, 'placeholder': _('Fale um pouco sobre você, máximo de 100 caracteres')}), 
        required=False,
        label=_("Sua Bio")
    )
    
    foto_perfil = forms.ImageField(
        label=_("Alterar Foto de Perfil"), 
        required=False, 
        widget=forms.FileInput
    )

    foto_capa = forms.ImageField(
        label=_("Alterar Imagem de Capa"), 
        required=False, 
        widget=forms.FileInput
    )

    class Meta:
        model = Usuario
        fields = ['nome', 'foto_perfil', 'foto_capa', 'bio']
        widgets = {
            'nome':  forms.Textarea(attrs={'rows': 3, 'maxlength': 150, 'minlength': 3}),
        }
        labels = {
            'nome': _('Seu Nome'),
        }