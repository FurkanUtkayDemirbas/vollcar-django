from django.db import models

class Firma(models.Model):
    sirket_kodu = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Şirket Kodu")
    ad = models.CharField(max_length=200, verbose_name="Şirket Adı")
    iletisim = models.CharField(max_length=100, null=True, blank=True, verbose_name="İletişim Bilgisi")
    
    def save(self, *args, **kwargs):
        if not self.sirket_kodu:
            try:
                last = Firma.objects.filter(sirket_kodu__startswith='SRK-').order_by('sirket_kodu').last()
                if last:
                    last_num = int(last.sirket_kodu.split('-')[1])
                    self.sirket_kodu = f"SRK-{last_num + 1:04d}"
                else:
                    self.sirket_kodu = "SRK-0001"
            except Exception:
                import uuid
                self.sirket_kodu = f"SRK-{str(uuid.uuid4())[:4].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.ad

class Personel(models.Model):
    CALISMA_TURLERI = [
        ('tam_zamanli', 'Tam Zamanlı'),
        ('yari_zamanli', 'Yarı Zamanlı'),
        ('serbest', 'Freelance/Sözleşmeli'),
    ]

    # ESKİ VERİLERİN KAYBOLMAMASI İÇİN BUNU SİLMİYORUZ
    ad_soyad = models.CharField(max_length=100, null=True, blank=True) 

    # YENİ ALANLAR (Şimdilik boş bırakılmalarına izin veriyoruz)
    ad = models.CharField(max_length=50, null=True, blank=True)
    soyad = models.CharField(max_length=50, null=True, blank=True)
    
    telefon = models.CharField(max_length=20)
    is_baslama_tarihi = models.DateField(null=True, blank=True)
    is_ayrilis_tarihi = models.DateField(null=True, blank=True)
    calisma_turu = models.CharField(max_length=20, choices=CALISMA_TURLERI, default='tam_zamanli')
    gorevi = models.CharField(max_length=100, null=True, blank=True)
    aktif_mi = models.BooleanField(default=True)

    def is_available(self, start_time, end_time, exclude_transfer_id=None):
        """
        Belirlenen zaman aralığında personelin (şoförün) müsait olup olmadığını kontrol eder.
        """
        if not self.aktif_mi:
            return False
            
        from django.db.models import Q
        from .models import Transfer
        
        # Çakışan Transferleri Kontrol Et
        overlapping_transfers = Transfer.objects.filter(
            personel=self,
            transfer_durumu__in=['beklemede', 'basladi']
        ).filter(
            Q(alis_saati__lt=end_time) & Q(varis_saati__gt=start_time)
        )
        
        if exclude_transfer_id:
            overlapping_transfers = overlapping_transfers.exclude(id=exclude_transfer_id)
            
        if overlapping_transfers.exists():
            return False
            
        return True

    def __str__(self):
        # Eğer yeni ad soyad girilmişse onu, girilmemişse eski ad_soyad'ı göster
        if self.ad and self.soyad:
            return f"{self.ad} {self.soyad}"
        return self.ad_soyad or "İsimsiz Personel"

class AracTuru(models.Model):
    kodu = models.CharField(max_length=50, unique=True, null=True, blank=True)
    tanimi = models.CharField(max_length=100)
    firma = models.ForeignKey('Firma', on_delete=models.CASCADE, null=True, blank=True, verbose_name="Şirket")

    def __str__(self):
        base = f"{self.kodu} - {self.tanimi}" if self.kodu else self.tanimi
        return f"{base} ({self.firma.ad})" if self.firma else base

class MasrafTuru(models.Model):
    tanimi = models.CharField(max_length=100)
    firma = models.ForeignKey('Firma', on_delete=models.CASCADE, null=True, blank=True, verbose_name="Şirket")

    def __str__(self):
        return f"{self.tanimi} ({self.firma.ad})" if self.firma else self.tanimi

class Arac(models.Model):
    VITES_SECENEKLERI = [
        ('manuel', 'Manuel'),
        ('otomatik', 'Otomatik'),
        ('yari_otomatik', 'Yarı Otomatik'),
    ]
    
    YAKIT_SECENEKLERI = [
        ('benzin', 'Benzin'),
        ('dizel', 'Dizel'),
        ('lpg', 'LPG'),
        ('elektrik', 'Elektrik'),
        ('hibrit', 'Hibrit'),
    ]
    
    DURUM_SECENEKLERI = [
        ('bosta', 'Faal (Boşta)'),
        ('musteride', 'Müşteride'),
        ('rehin', 'Rehin'),
        ('serviste', 'Serviste'),
    ]
    
    MULKIYET_SECENEKLERI = [
        ('sirket', 'Şirket Aracı'),
        ('kiralik', 'Kiralık'),
    ]

    IL_SECENEKLERI = [
        ('01', '01 - Adana'), ('02', '02 - Adıyaman'), ('03', '03 - Afyonkarahisar'),
        ('04', '04 - Ağrı'), ('05', '05 - Amasya'), ('06', '06 - Ankara'),
        ('07', '07 - Antalya'), ('08', '08 - Artvin'), ('09', '09 - Aydın'),
        ('10', '10 - Balıkesir'), ('11', '11 - Bilecik'), ('12', '12 - Bingöl'),
        ('13', '13 - Bitlis'), ('14', '14 - Bolu'), ('15', '15 - Burdur'),
        ('16', '16 - Bursa'), ('17', '17 - Çanakkale'), ('18', '18 - Çankırı'),
        ('19', '19 - Çorum'), ('20', '20 - Denizli'), ('21', '21 - Diyarbakır'),
        ('22', '22 - Edirne'), ('23', '23 - Elazığ'), ('24', '24 - Erzincan'),
        ('25', '25 - Erzurum'), ('26', '26 - Eskişehir'), ('27', '27 - Gaziantep'),
        ('28', '28 - Giresun'), ('29', '29 - Gümüşhane'), ('30', '30 - Hakkari'),
        ('31', '31 - Hatay'), ('32', '32 - Isparta'), ('33', '33 - Mersin'),
        ('34', '34 - İstanbul'), ('35', '35 - İzmir'), ('36', '36 - Kars'),
        ('37', '37 - Kastamonu'), ('38', '38 - Kayseri'), ('39', '39 - Kırklareli'),
        ('40', '40 - Kırşehir'), ('41', '41 - Kocaeli'), ('42', '42 - Konya'),
        ('43', '43 - Kütahya'), ('44', '44 - Malatya'), ('45', '45 - Manisa'),
        ('46', '46 - Kahramanmaraş'), ('47', '47 - Mardin'), ('48', '48 - Muğla'),
        ('49', '49 - Muş'), ('50', '50 - Nevşehir'), ('51', '51 - Niğde'),
        ('52', '52 - Ordu'), ('53', '53 - Rize'), ('54', '54 - Sakarya'),
        ('55', '55 - Samsun'), ('56', '56 - Siirt'), ('57', '57 - Sinop'),
        ('58', '58 - Sivas'), ('59', '59 - Tekirdağ'), ('60', '60 - Tokat'),
        ('61', '61 - Trabzon'), ('62', '62 - Tunceli'), ('63', '63 - Şanlıurfa'),
        ('64', '64 - Uşak'), ('65', '65 - Van'), ('66', '66 - Yozgat'),
        ('67', '67 - Zonguldak'), ('68', '68 - Aksaray'), ('69', '69 - Bayburt'),
        ('70', '70 - Karaman'), ('71', '71 - Kırıkkale'), ('72', '72 - Batman'),
        ('73', '73 - Şırnak'), ('74', '74 - Bartın'), ('75', '75 - Ardahan'),
        ('76', '76 - Iğdır'), ('77', '77 - Yalova'), ('78', '78 - Karabük'),
        ('79', '79 - Kilis'), ('80', '80 - Osmaniye'), ('81', '81 - Düzce')
    ]

    arac_kodu = models.CharField(max_length=50, unique=True, null=True, blank=True)
    plaka = models.CharField(max_length=20, unique=True)
    kapasite = models.PositiveIntegerField(default=4)
    
    il_kodu = models.CharField(max_length=10, choices=IL_SECENEKLERI, null=True, blank=True)
    firma = models.ForeignKey('Firma', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Şirket")
    arac_turu = models.ForeignKey(AracTuru, on_delete=models.SET_NULL, null=True, blank=True)
    tescil_sira_no = models.CharField(max_length=50, null=True, blank=True)
    renk = models.CharField(max_length=30, null=True, blank=True)
    sase_no = models.CharField(max_length=100, null=True, blank=True)
    motor_no = models.CharField(max_length=100, null=True, blank=True)
    marka = models.CharField(max_length=50, null=True, blank=True)
    model_tanim = models.CharField(max_length=100, null=True, blank=True)
    vites = models.CharField(max_length=20, choices=VITES_SECENEKLERI, null=True, blank=True)
    yakit_tipi = models.CharField(max_length=20, choices=YAKIT_SECENEKLERI, null=True, blank=True)
    arac_durumu = models.CharField(max_length=20, choices=DURUM_SECENEKLERI, default='bosta')
    arac_kimde = models.CharField(max_length=100, null=True, blank=True)
    
    ilk_tescil_tarihi = models.DateField(null=True, blank=True)
    tescil_tarihi = models.DateField(null=True, blank=True)
    model_yili = models.PositiveIntegerField(null=True, blank=True)
    segment = models.CharField(max_length=50, null=True, blank=True)
    mulkiyet_durumu = models.CharField(max_length=20, choices=MULKIYET_SECENEKLERI, default='sirket')
    
    muayene_tarihi = models.DateField(null=True, blank=True)
    egzoz_emisyon_tarihi = models.DateField(null=True, blank=True)
    cekici_ruhsati_tarihi = models.DateField(null=True, blank=True)
    serusefer_tarihi = models.DateField(null=True, blank=True)
    
    resim = models.ImageField(upload_to='arac_resimleri/', null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.arac_kodu:
            try:
                last_arac = Arac.objects.filter(arac_kodu__startswith='ARC-').order_by('arac_kodu').last()
                if last_arac:
                    last_num = int(last_arac.arac_kodu.split('-')[1])
                    self.arac_kodu = f"ARC-{last_num + 1:04d}"
                else:
                    self.arac_kodu = "ARC-0001"
            except Exception:
                import uuid
                self.arac_kodu = f"ARC-{str(uuid.uuid4())[:4].upper()}"
        super().save(*args, **kwargs)

    def is_available(self, start_time, end_time, exclude_transfer_id=None):
        """
        Belirlenen zaman aralığında aracın müsait olup olmadığını kontrol eder.
        """
        # 1. Manuel durum kontrolü
        if self.arac_durumu in ['rehin', 'serviste', 'musteride']:
            return False
            
        from django.db.models import Q
        from .models import Transfer, Kiralama
        
        # 2. Çakışan Transferleri Kontrol Et
        # Transfer durumu 'iptal' veya 'tamamlandi' değilse ve zamanlar çakışıyorsa meşguldür.
        overlapping_transfers = Transfer.objects.filter(
            arac_kodu=self,
            transfer_durumu__in=['beklemede', 'basladi']
        ).filter(
            Q(alis_saati__lt=end_time) & Q(varis_saati__gt=start_time)
        )
        
        if exclude_transfer_id:
            overlapping_transfers = overlapping_transfers.exclude(id=exclude_transfer_id)
            
        if overlapping_transfers.exists():
            return False

        # 3. Çakışan Kiralamaları Kontrol Et
        # Kiralama tarihleri Date olduğu için DateTime'ı Date'e çeviriyoruz
        start_date = start_time.date()
        end_date = end_time.date()
        
        overlapping_kiralamas = Kiralama.objects.filter(
            arac=self
        ).filter(
            Q(baslangic_tarihi__lte=end_date) & Q(bitis_tarihi__gte=start_date)
        )
        
        if overlapping_kiralamas.exists():
            return False
            
        return True

    @property
    def current_availability(self):
        """
        Şu anki müsaitlik durumunu kontrol eder.
        """
        from django.utils import timezone
        now = timezone.now()
        # Çok kısa bir aralık için kontrol edebiliriz
        return self.is_available(now, now + timezone.timedelta(minutes=1))

    def __str__(self):
        return f"{self.plaka} - {self.marka}"

class Sigorta(models.Model):
    SIGORTA_TURLERI = [
        ('trafik', 'Trafik Sigortası'),
        ('kasko', 'Kasko'),
        ('ihtiyari', 'İhtiyari Mali Mesuliyet (İMM)'),
        ('ferdi_kaza', 'Koltuk Ferdi Kaza'),
    ]

    arac = models.ForeignKey(Arac, on_delete=models.CASCADE, related_name='sigortalar')
    sigorta_sirketi = models.CharField(max_length=100, null=True, blank=True, verbose_name="Sigorta Şirketi")
    sigorta_turu = models.CharField(max_length=50, choices=SIGORTA_TURLERI, default='trafik', verbose_name="Sigorta Türü")
    police_no = models.CharField(max_length=100)
    police_tarihi = models.DateField()
    police_bitis_tarihi = models.DateField()
    tutar = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.arac.plaka} - {self.police_no}"

class Hasar(models.Model):
    arac = models.ForeignKey(Arac, on_delete=models.CASCADE, related_name='hasarlar')
    dosya_no = models.CharField(max_length=100)
    hasar_turu = models.CharField(max_length=100)
    hasar_tarihi = models.DateField()
    ekspertiz = models.CharField(max_length=200, null=True, blank=True)
    muafiyet_tutari = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.arac.plaka} - {self.dosya_no}"

class Bakim(models.Model):
    arac = models.ForeignKey(Arac, on_delete=models.CASCADE, related_name='bakimlar')
    bakim_km = models.PositiveIntegerField()
    sonraki_bakim_tarihi = models.DateField(null=True, blank=True)
    sonraki_bakim_km = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.arac.plaka} - {self.bakim_km} KM Bakımı"

class Transfer(models.Model):
    TRANSFER_TURLERI = [
        ('gidis', 'Gidiş'),
        ('donus', 'Dönüş'),
        ('gidis_donus', 'Gidiş-Dönüş'),
    ]
    VARIS_TURLERI = [
        ('havalimani', 'Havalimanı'),
        ('gar', 'Gar'),
        ('kamu', 'Kamu Kurumu'),
        ('otel', 'Otel'),
        ('ev', 'Ev'),
        ('diger', 'Diğer'),
    ]
    CIKIS_TURLERI = [
        ('havalimani', 'Havalimanı'),
        ('gar', 'Gar'),
        ('kamu', 'Kamu Kurumu'),
        ('otel', 'Otel'),
        ('ev', 'Ev'),
        ('diger', 'Diğer'),
    ]
    ODEME_TURLERI = [
        ('nakit', 'Nakit'),
        ('kredi_karti', 'Kredi Kartı'),
        ('havale', 'Havale/EFT'),
        ('cari', 'Cari Hesap'),
    ]
    DURUM_SECENEKLERI = [
        ('beklemede', 'Beklemede'),
        ('basladi', 'Başladı'),
        ('tamamlandi', 'Tamamlandı'),
        ('iptal', 'İptal Edildi'),
    ]

    musteri_adi = models.CharField(max_length=100, null=True, blank=True, verbose_name="Eski Müşteri Adı")
    musteri_kodu = models.CharField(max_length=50, null=True, blank=True)
    musteri_telefon = models.CharField(max_length=20, null=True, blank=True)
    musteri_mail = models.EmailField(null=True, blank=True)

    # Yeni eklenen Muhatap ilişkisi
    muhatap = models.ForeignKey('Muhatap', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Müşteri (Muhatap)")
    
    transfer_turu = models.CharField(max_length=20, choices=TRANSFER_TURLERI)
    transfer_durumu = models.CharField(max_length=20, choices=DURUM_SECENEKLERI, default='beklemede')
    
    alis_yeri = models.TextField(verbose_name="Çıkış Adresi")
    alis_yer_turu = models.CharField(max_length=20, choices=CIKIS_TURLERI, null=True, blank=True, verbose_name="Çıkış Adresi Türü")
    alis_saati = models.DateTimeField(verbose_name="Çıkış Saati")
    varis_yeri = models.TextField(verbose_name="Varış Adresi")
    varis_yer_turu = models.CharField(max_length=20, choices=VARIS_TURLERI, verbose_name="Varış Adresi Türü")
    varis_saati = models.DateTimeField(null=True, blank=True, verbose_name="Varış Saati")
    
    sefer_no = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Sefer No")
    kisi_sayisi = models.PositiveIntegerField(default=1)
    cocuk_sayisi = models.PositiveIntegerField(default=0)
    bebek_sayisi = models.PositiveIntegerField(default=0)
    
    yolcu_geldi_mi = models.BooleanField(default=False, verbose_name="Yolcu Geldi mi?")
    
    personel = models.ForeignKey(Personel, on_delete=models.SET_NULL, null=True, blank=True)
    arac_kodu = models.ForeignKey(Arac, on_delete=models.SET_NULL, null=True, blank=True)
    
    tutar = models.DecimalField(max_digits=10, decimal_places=2)
    odeme_turu = models.CharField(max_length=20, choices=ODEME_TURLERI)
    odendi_mi = models.BooleanField(default=False)
    faturalama_durumu = models.BooleanField(default=False)

    def __str__(self):
        musteri_isim = self.muhatap.unvan if self.muhatap else self.musteri_adi
        return f"{musteri_isim} - {self.alis_yeri} > {self.varis_yeri}"

class TransferYolcu(models.Model):
    YOLCU_TURLERI = [
        ('yetiskin', 'Yetişkin'),
        ('cocuk', 'Çocuk'),
        ('bebek', 'Bebek'),
    ]
    transfer = models.ForeignKey(Transfer, on_delete=models.CASCADE, related_name='yolcular_listesi')
    isim_soyisim = models.CharField(max_length=150, verbose_name="İsim Soyisim")
    telefon = models.CharField(max_length=50, null=True, blank=True, verbose_name="Telefon Numarası")
    yolcu_turu = models.CharField(max_length=20, choices=YOLCU_TURLERI, default='yetiskin', verbose_name="Yolcu Türü")

    def __str__(self):
        return f"{self.isim_soyisim} ({self.get_yolcu_turu_display()}) - {self.telefon}"


class Masraf(models.Model):
    PARA_BIRIMLERI = [
        ('TRY', 'Türk Lirası (₺)'),
        ('USD', 'Dolar ($)'),
        ('EUR', 'Euro (€)'),
    ]

    # İlişkiler (Masraf kime/neye ait?)
    firma = models.ForeignKey('Firma', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Şirket")
    arac = models.ForeignKey(Arac, on_delete=models.SET_NULL, null=True, blank=True, related_name='masraflar', verbose_name="İlgili Araç")
    personel = models.ForeignKey(Personel, on_delete=models.SET_NULL, null=True, blank=True, related_name='masraflar', verbose_name="İlgili Personel")
    
    # Masraf Detayları
    masraf_turu = models.ForeignKey('MasrafTuru', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Masraf Türü")
    tarih = models.DateField(verbose_name="Masraf Tarihi")
    tutar = models.DecimalField(max_digits=10, decimal_places=2)
    para_birimi = models.CharField(max_length=5, choices=PARA_BIRIMLERI, default='TRY')
    fis_no = models.CharField(max_length=50, null=True, blank=True, verbose_name="Fiş / Fatura No")
    aciklama = models.TextField(null=True, blank=True, verbose_name="Açıklama / Detay")
    
    # Dosya Yükleme (Resim veya PDF)
    belge = models.FileField(upload_to='masraf_belgeleri/', null=True, blank=True, verbose_name="Fatura/Fiş Belgesi (PDF/Resim)")

    def __str__(self):
        turu = self.masraf_turu.tanimi if self.masraf_turu else "Belirtilmemiş"
        return f"{turu} - {self.tutar} {self.para_birimi} ({self.tarih})"


class Ceza(models.Model):
    # İlişkiler
    arac = models.ForeignKey(Arac, on_delete=models.CASCADE, related_name='cezalar', verbose_name="Ceza Yiyen Araç")
    personel = models.ForeignKey(Personel, on_delete=models.SET_NULL, null=True, blank=True, related_name='cezalar', verbose_name="Aracı Kullanan Personel")
    
    # Ceza Detayları
    tarih = models.DateField(verbose_name="Ceza Tarihi")
    saat = models.TimeField(null=True, blank=True, verbose_name="Ceza Saati")
    madde = models.CharField(max_length=200, verbose_name="Ceza Maddesi / İhlal Nedeni (Örn: Radar, Hatalı Park)")
    tutar = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ceza Tutarı (₺)")
    
    # Ödeme Durumu
    son_odeme_tarihi = models.DateField(null=True, blank=True, verbose_name="İndirimli Son Ödeme Tarihi")
    odendi_mi = models.BooleanField(default=False, verbose_name="Ödendi mi?")
    
    aciklama = models.TextField(null=True, blank=True, verbose_name="Açıklama / Notlar")
    belge = models.FileField(upload_to='ceza_belgeleri/', null=True, blank=True, verbose_name="Ceza Makbuzu / Fotoğrafı")

    def __str__(self):
        return f"{self.arac.plaka} - {self.madde} (₺{self.tutar})"

class Kiralama(models.Model):
    SURE_BIRIMI_SECENEKLERI = [
        ('gun', 'Gün'),
        ('ay', 'Ay'),
        ('yil', 'Yıl'),
    ]

    # Araç seçildiğinde Marka, Model, Renk vb. otomatik olarak bu ilişkiden gelecek
    arac = models.ForeignKey(Arac, on_delete=models.CASCADE, related_name='kiralamalar', verbose_name="Kiralanan Araç")
    
    # Teklif Bilgileri
    teklif_baslangic = models.DateField(null=True, blank=True, verbose_name="Teklif Başlangıç Tarihi")
    teklif_gecerlilik_sonu = models.DateField(null=True, blank=True, verbose_name="Teklif Geçerlilik Sonu")
    
    # Kiralama Detayları
    baslangic_tarihi = models.DateField(verbose_name="Kiralama Başlangıç Tarihi")
    bitis_tarihi = models.DateField(verbose_name="Kiralama Bitiş Tarihi")
    sure = models.PositiveIntegerField(verbose_name="Süre")
    sure_birimi = models.CharField(max_length=10, choices=SURE_BIRIMI_SECENEKLERI, default='gun', verbose_name="Süre Birimi")
    
    # Finans
    birim_fiyat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Birim Fiyat (₺)")
    toplam_tutar = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Toplam Tutar (₺)")
    
    # Sözleşme ve Müşteri
    sozlesme_imzalandi = models.BooleanField(default=False, verbose_name="Sözleşme İmzalandı mı?")
    teslim_edilen_kisiler = models.CharField(max_length=200, null=True, blank=True, verbose_name="Eski - Teslim Edilen Kişi / Kurum")
    
    # Yeni eklenen Muhatap ilişkisi
    muhatap = models.ForeignKey('Muhatap', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Müşteri (Muhatap)")

    def __str__(self):
        musteri_isim = self.muhatap.unvan if self.muhatap else self.teslim_edilen_kisiler
        return f"{self.arac.plaka} - {musteri_isim} ({self.baslangic_tarihi})"

class Muhatap(models.Model):
    musteri_kodu = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Müşteri Kodu")
    unvan = models.CharField(max_length=100, unique=True, verbose_name="Müşteri Adı / Ünvan")
    vkn = models.CharField(max_length=11, null=True, blank=True, verbose_name="VKN / TCKN")
    eposta = models.EmailField(null=True, blank=True, verbose_name="E-Posta")
    telefon = models.CharField(max_length=15, null=True, blank=True, verbose_name="Telefon")
    adres = models.TextField(null=True, blank=True, verbose_name="Açık Adres")
    il = models.CharField(max_length=50, choices=Arac.IL_SECENEKLERI, null=True, blank=True, verbose_name="İl")
    ilce = models.CharField(max_length=50, null=True, blank=True, verbose_name="İlçe")
    vergi_dairesi = models.CharField(max_length=100, null=True, blank=True, verbose_name="Vergi Dairesi")
    slug = models.SlugField(max_length=100, unique=True, null=True, blank=True)
    aktif = models.BooleanField(default=True, null=True, verbose_name="Aktif mi?")
    
    def save(self, *args, **kwargs):
        if not self.musteri_kodu:
            try:
                last = Muhatap.objects.filter(musteri_kodu__startswith='MST-').order_by('musteri_kodu').last()
                if last:
                    last_num = int(last.musteri_kodu.split('-')[1])
                    self.musteri_kodu = f"MST-{last_num + 1:04d}"
                else:
                    self.musteri_kodu = "MST-0001"
            except Exception:
                import uuid
                self.musteri_kodu = f"MST-{str(uuid.uuid4())[:4].upper()}"
        if not self.slug and self.unvan:
            from django.utils.text import slugify
            self.slug = slugify(self.unvan.replace('ı', 'i').replace('ş', 's').replace('ğ', 'g').replace('ö', 'o').replace('ç', 'c').replace('ü', 'u'))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.unvan