from django import forms
from django.db.models import Q
from .models import Transfer, Arac, Personel, Sigorta, Hasar, Bakim, Masraf, Ceza, Firma, Kiralama, Muhatap, AracTuru, MasrafTuru

class AracTuruForm(forms.ModelForm):
    class Meta:
        model = AracTuru
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-input'

class MasrafTuruForm(forms.ModelForm):
    class Meta:
        model = MasrafTuru
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-input'

class PersonelForm(forms.ModelForm):
    class Meta:
        model = Personel
        exclude = ['ad_soyad']
        widgets = {
            'is_baslama_tarihi': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'is_ayrilis_tarihi': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['is_baslama_tarihi', 'is_ayrilis_tarihi']:
                if not isinstance(field.widget, forms.CheckboxInput):
                    field.widget.attrs['class'] = 'form-input'

                    
class TransferForm(forms.ModelForm):
    class Meta:
        model = Transfer
        exclude = ['kisi_sayisi', 'cocuk_sayisi', 'bebek_sayisi', 'musteri_adi', 'musteri_kodu', 'musteri_telefon', 'musteri_mail']
        widgets = {
            'alis_saati': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-input'},
                format='%Y-%m-%dT%H:%M'
            ),
            'varis_saati': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-input'},
                format='%Y-%m-%dT%H:%M'
            ),
            'alis_yeri': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'varis_yeri': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['alis_saati', 'varis_saati']:
                if not isinstance(field.widget, forms.CheckboxInput):
                    field.widget.attrs['class'] = 'form-input'
                    
        if 'arac_kodu' in self.fields:
            if hasattr(self.instance, 'arac_kodu') and self.instance.arac_kodu:
                self.fields['arac_kodu'].queryset = Arac.objects.filter(Q(arac_durumu='bosta') | Q(id=self.instance.arac_kodu.id))
            else:
                self.fields['arac_kodu'].queryset = Arac.objects.filter(arac_durumu='bosta')

    def clean_sefer_no(self):
        sefer_no = self.cleaned_data.get('sefer_no')
        if sefer_no:
            qs = Transfer.objects.filter(sefer_no=sefer_no)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f'"{sefer_no}" sefer numarası zaten kullanılıyor. Lütfen farklı bir sefer numarası girin.'
                )
        return sefer_no

    def clean(self):
        cleaned_data = super().clean()
        arac = cleaned_data.get('arac_kodu')
        personel = cleaned_data.get('personel')
        alis_saati = cleaned_data.get('alis_saati')
        varis_saati = cleaned_data.get('varis_saati')

        from django.utils import timezone

        # 1. Çıkış tarihi bugünden önce olamaz — SADECE yeni kayıt eklerken kontrol et
        is_new_record = not (self.instance and self.instance.pk)
        if is_new_record and alis_saati and alis_saati < timezone.now():
            self.add_error('alis_saati', 'Çıkış tarihi geçmişte olamaz.')

        if alis_saati and varis_saati:

            # 2. Varış tarihi (gün olarak) çıkış tarihinden önce olamaz
            # Saat farklı olabilir, ama gün olarak geçmişe gidemez
            if varis_saati.date() < alis_saati.date():
                self.add_error('varis_saati', 'Varış tarihi, çıkış tarihinden önce olamaz.')

            # 3. Araç müsaitlik kontrolü
            if arac:
                if not arac.is_available(alis_saati, varis_saati, exclude_transfer_id=self.instance.id):
                    self.add_error(
                        'arac_kodu',
                        f'{arac.plaka} plakalı araç seçilen tarih aralığında başka bir transfer veya kiralama için atanmış durumda.'
                    )

            # 4. Şoför müsaitlik kontrolü
            if personel:
                if not personel.is_available(alis_saati, varis_saati, exclude_transfer_id=self.instance.id):
                    self.add_error(
                        'personel',
                        f'{personel} isimli personel seçilen tarih aralığında başka bir transferde görevli.'
                    )

        return cleaned_data

        
class AracForm(forms.ModelForm):
    class Meta:
        model = Arac
        fields = '__all__'
        widgets = {
            'ilk_tescil_tarihi': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'tescil_tarihi': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'muayene_tarihi': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'egzoz_emisyon_tarihi': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'cekici_ruhsati_tarihi': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'serusefer_tarihi': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'arac_kodu': forms.TextInput(attrs={'class': 'form-input', 'readonly': 'readonly', 'placeholder': 'Sistem Tarafından Otomatik Verilecektir'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in self.Meta.widgets or field_name == 'arac_kodu':
                if not isinstance(field.widget, forms.CheckboxInput) and not isinstance(field.widget, forms.FileInput):
                    field.widget.attrs['class'] = 'form-input'

class FirmaForm(forms.ModelForm):
    class Meta:
        model = Firma
        fields = '__all__'
        widgets = {
            'ad': forms.TextInput(attrs={'class': 'form-input'}),
            'iletisim': forms.TextInput(attrs={'class': 'form-input'}),
        }

class SigortaForm(forms.ModelForm):
    class Meta:
        model = Sigorta
        fields = ['arac', 'sigorta_sirketi', 'sigorta_turu', 'police_no', 'police_tarihi', 'police_bitis_tarihi', 'tutar']
        
        widgets = {
            'arac': forms.Select(attrs={'class': 'form-input'}),
            'sigorta_sirketi': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Örn: Allianz, Axa'}),
            'sigorta_turu': forms.Select(attrs={'class': 'form-input'}),
            'police_tarihi': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'police_bitis_tarihi': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'police_no': forms.TextInput(attrs={'class': 'form-input'}),
            'tutar': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
        }

class HasarForm(forms.ModelForm):
    class Meta:
        model = Hasar
        exclude = ['arac']
        widgets = {
            'hasar_tarihi': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'dosya_no': forms.TextInput(attrs={'class': 'form-input'}),
            'hasar_turu': forms.TextInput(attrs={'class': 'form-input'}),
            'ekspertiz': forms.TextInput(attrs={'class': 'form-input'}),
            'muafiyet_tutari': forms.NumberInput(attrs={'class': 'form-input'}),
        }

class BakimForm(forms.ModelForm):
    class Meta:
        model = Bakim
        exclude = ['arac']
        widgets = {
            'sonraki_bakim_tarihi': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'bakim_km': forms.NumberInput(attrs={'class': 'form-input'}),
            'sonraki_bakim_km': forms.NumberInput(attrs={'class': 'form-input'}),
        }



class MasrafForm(forms.ModelForm):
    class Meta:
        model = Masraf
        fields = '__all__'
        widgets = {
            'tarih': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'aciklama': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Masraf ile ilgili detaylı açıklama...'}),
            'belge': forms.FileInput(attrs={'class': 'form-input', 'accept': '.pdf,image/*'}) # Sadece resim ve PDF kabul et
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['tarih', 'aciklama', 'belge']:
                if not isinstance(field.widget, forms.CheckboxInput):
                    field.widget.attrs['class'] = 'form-input'


class CezaForm(forms.ModelForm):
    class Meta:
        model = Ceza
        fields = '__all__'
        widgets = {
            'tarih': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'saat': forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'}),
            'son_odeme_tarihi': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'aciklama': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Ceza ile ilgili detaylı bilgi...'}),
            'belge': forms.FileInput(attrs={'class': 'form-input', 'accept': '.pdf,image/*'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['tarih', 'saat', 'son_odeme_tarihi', 'aciklama', 'belge']:
                if not isinstance(field.widget, forms.CheckboxInput):
                    field.widget.attrs['class'] = 'form-input'

class KiralamaForm(forms.ModelForm):
    class Meta:
        model = Kiralama
        exclude = ['teslim_edilen_kisiler']
        widgets = {
            'teklif_baslangic': forms.DateInput(attrs={'type': 'date'}),
            'teklif_gecerlilik_sonu': forms.DateInput(attrs={'type': 'date'}),
            'baslangic_tarihi': forms.DateInput(attrs={'type': 'date'}),
            'bitis_tarihi': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-input'
        
        if 'arac' in self.fields:
            if hasattr(self.instance, 'arac') and self.instance.arac:
                self.fields['arac'].queryset = Arac.objects.filter(Q(arac_durumu='bosta') | Q(id=self.instance.arac.id))
                self.fields['arac'].queryset = Arac.objects.filter(arac_durumu='bosta')

class MuhatapForm(forms.ModelForm):
    il = forms.ChoiceField(
        choices=[('', 'İl Seçiniz')] + Arac.IL_SECENEKLERI,
        required=False,
        widget=forms.Select(attrs={'class': 'form-input'})
    )

    class Meta:
        model = Muhatap
        exclude = ['slug']
        widgets = {
            'musteri_kodu': forms.TextInput(attrs={'class': 'form-input', 'readonly': 'readonly', 'placeholder': 'Sistem Tarafından Otomatik Verilecektir'}),
            'unvan': forms.TextInput(attrs={'class': 'form-input'}),
            'vkn': forms.TextInput(attrs={'class': 'form-input'}),
            'eposta': forms.EmailInput(attrs={'class': 'form-input'}),
            'telefon': forms.TextInput(attrs={'class': 'form-input'}),
            'adres': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'ilce': forms.TextInput(attrs={'class': 'form-input'}),
            'vergi_dairesi': forms.TextInput(attrs={'class': 'form-input'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-input'

class MusteriTransferForm(forms.ModelForm):
    class Meta:
        model = Transfer
        # Müşterinin sadece doldurması/görmesi gereken alanları buraya ekledik. 
        fields = [
            'transfer_turu', 
            'alis_yeri', 
            'alis_yer_turu', 
            'alis_saati', 
            'varis_yeri', 
            'varis_yer_turu', 
            'varis_saati', 
            'sefer_no', 
            'odeme_turu',
            'tutar'
        ]
        
        widgets = {
            'alis_saati': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-input'}),
            'varis_saati': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-input'}),
            'alis_yeri': forms.Textarea(attrs={'rows': 2, 'class': 'form-input'}),
            'varis_yeri': forms.Textarea(attrs={'rows': 2, 'class': 'form-input'}),
            'tutar': forms.NumberInput(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-input'