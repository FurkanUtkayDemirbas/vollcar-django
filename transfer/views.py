from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.db.models import Q , Sum , Prefetch
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from datetime import date, timedelta
from .models import Transfer, Arac, Personel, Masraf, Ceza, Kiralama, Muhatap, Firma, AracTuru, MasrafTuru, Sigorta
from .forms import TransferForm, AracForm, PersonelForm, MasrafForm, CezaForm, KiralamaForm, MuhatapForm, FirmaForm, AracTuruForm, MasrafTuruForm, SigortaForm , MusteriTransferForm


@login_required
def dashboard(request):
    toplam_transfer = Transfer.objects.count()
    bekleyen_transfer = Transfer.objects.filter(transfer_durumu='beklemede').count()
    tamamlanan_transfer = Transfer.objects.filter(transfer_durumu='tamamlandi').count()
    toplam_kazanc = Transfer.objects.filter(transfer_durumu='tamamlandi').aggregate(Sum('tutar'))['tutar__sum'] or 0

    context = {
        'toplam_transfer': toplam_transfer,
        'bekleyen_transfer': bekleyen_transfer,
        'tamamlanan_transfer': tamamlanan_transfer,
        'toplam_kazanc': toplam_kazanc,
    }
    return render(request, 'transfer/dashboard.html', context)

def kayit_ol(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # YENİ: Kayıt olan kullanıcı için otomatik Muhatap (Müşteri) oluştur
            try:
                Muhatap.objects.get_or_create(unvan=user.username)
            except Exception as e:
                pass
                
            login(request, user)
            return redirect('transfer_listesi')
    else:
        form = UserCreationForm()
    
    return render(request, 'transfer/kayit.html', {'form': form})

def giris_yap(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # --- ROL KONTROLÜ VE YÖNLENDİRME ---
            if user.is_staff:
                # Yönetici (Admin/Personel) ise Dashboard'a gitsin
                return redirect('dashboard')
            else:
                # Normal kullanıcı (Müşteri) ise doğrudan talep oluşturmaya gitsin
                return redirect('transfer_ekle')
            # -----------------------------------
    else:
        form = AuthenticationForm()
        
    return render(request, 'transfer/giris.html', {'form': form})

def cikis_yap(request):
    logout(request)
    return redirect('giris_yap')

@login_required
def transfer_listesi(request):
    query = request.GET.get('q', '')
    durum = request.GET.get('durum', '')

    # YENİ: ROL KONTROLÜ
    if request.user.is_staff:
        # Adminse hepsini görsün
        transferler = Transfer.objects.all().order_by('-tutar', '-alis_saati')
    else:
        # Müşteriyse sadece kendininkini görsün
        transferler = Transfer.objects.filter(musteri_adi=request.user.username).order_by('-tutar', '-alis_saati')

    if query:
        transferler = transferler.filter(
            Q(musteri_adi__icontains=query) |
            Q(alis_yeri__icontains=query) |
            Q(varis_yeri__icontains=query)
        )

    if durum:
        transferler = transferler.filter(transfer_durumu=durum)

    context = {
        'transferler': transferler,
        'query': query,
        'durum': durum,
        'DURUMLAR': Transfer.DURUM_SECENEKLERI
    }
    return render(request, 'transfer/transfer_listesi.html', context)

@login_required
def transfer_talep_listesi(request):
    if not request.user.is_staff:
        # Eğer admin değilse bu sayfaya giremesin
        return redirect('dashboard')
        
    query = request.GET.get('q', '')
    durum = request.GET.get('durum', '')

    # Sadece müşteriler tarafından oluşturulan talepler (muhatap_id atanmamış veya musteri_adi dolu vb.)
    # Veya direkt musteri_adi boş olmayanlar (biz müşteri eklerken username'i musteri_adi alanına atıyoruz)
    transferler = Transfer.objects.filter(musteri_adi__isnull=False).exclude(musteri_adi="").order_by('-alis_saati')

    if query:
        transferler = transferler.filter(
            Q(musteri_adi__icontains=query) |
            Q(alis_yeri__icontains=query) |
            Q(varis_yeri__icontains=query)
        )

    if durum:
        transferler = transferler.filter(transfer_durumu=durum)

    context = {
        'transferler': transferler,
        'query': query,
        'durum': durum,
        'DURUMLAR': Transfer.DURUM_SECENEKLERI,
        'is_talep_listesi': True  # Şablonda başlığı değiştirebilmek için
    }
    # Burada isterseniz transfer_listesi.html'yi tekrar kullanabiliriz, çünkü tablo aynı. Sadece title değişecek.
    return render(request, 'transfer/transfer_listesi.html', context)


@login_required
def transfer_ekle(request):
    # YENİ: HANGİ FORMU KULLANACAĞIZ?
    if request.user.is_staff:
        KullanilacakForm = TransferForm
    else:
        KullanilacakForm = MusteriTransferForm

    if request.method == 'POST':
        form = KullanilacakForm(request.POST)
        if form.is_valid():
            transfer = form.save(commit=False)
            
            # YENİ: MÜŞTERİYSE BİLGİLERİ OTOMATİK DOLDUR
            if not request.user.is_staff:
                transfer.musteri_adi = request.user.username
                transfer.transfer_durumu = 'beklemede'
                
                # Müşteri (Muhatap) kaydı varsa (veya yoksa oluşturarak) transfere bağla
                try:
                    muhatap, created = Muhatap.objects.get_or_create(unvan=request.user.username, defaults={'eposta': request.user.email})
                    transfer.muhatap = muhatap
                except Exception as e:
                    pass
                
            transfer.save()
            
            # YOLCU EKLEME KISMI (Senin kodun, tamamen aynı)
            isimler = request.POST.getlist('yolcu_isim[]')
            telefonlar = request.POST.getlist('yolcu_telefon[]')
            turler = request.POST.getlist('yolcu_turu[]')
            
            yetiskin_sayisi = 0
            cocuk_sayisi = 0
            bebek_sayisi = 0
            
            from .models import TransferYolcu
            for ad, tel, tur in zip(isimler, telefonlar, turler):
                if ad and ad.strip():
                    TransferYolcu.objects.create(transfer=transfer, isim_soyisim=ad.strip(), telefon=tel.strip() if tel else None, yolcu_turu=tur)
                    if tur == 'yetiskin':
                        yetiskin_sayisi += 1
                    elif tur == 'cocuk':
                        cocuk_sayisi += 1
                    elif tur == 'bebek':
                        bebek_sayisi += 1
            
            transfer.kisi_sayisi = yetiskin_sayisi
            transfer.cocuk_sayisi = cocuk_sayisi
            transfer.bebek_sayisi = bebek_sayisi
            transfer.save()
            
            return redirect('transfer_listesi')
    else:
        form = KullanilacakForm()
    
    return render(request, 'transfer/transfer_ekle.html', {'form': form})

from django.shortcuts import render, redirect, get_object_or_404

@login_required
def transfer_duzenle(request, id):
    transfer = get_object_or_404(Transfer, id=id)
    
    if request.user.is_staff:
        KullanilacakForm = TransferForm
    else:
        KullanilacakForm = MusteriTransferForm

    if request.method == 'POST':
        form = KullanilacakForm(request.POST, instance=transfer)
        if form.is_valid():
            form.save()
            isimler = request.POST.getlist('yolcu_isim[]')
            telefonlar = request.POST.getlist('yolcu_telefon[]')
            turler = request.POST.getlist('yolcu_turu[]')
            
            transfer.yolcular_listesi.all().delete()
            
            yetiskin_sayisi = 0
            cocuk_sayisi = 0
            bebek_sayisi = 0
            
            from .models import TransferYolcu
            for ad, tel, tur in zip(isimler, telefonlar, turler):
                if ad and ad.strip():
                    TransferYolcu.objects.create(transfer=transfer, isim_soyisim=ad.strip(), telefon=tel.strip() if tel else None, yolcu_turu=tur)
                    if tur == 'yetiskin':
                        yetiskin_sayisi += 1
                    elif tur == 'cocuk':
                        cocuk_sayisi += 1
                    elif tur == 'bebek':
                        bebek_sayisi += 1
            
            transfer.kisi_sayisi = yetiskin_sayisi
            transfer.cocuk_sayisi = cocuk_sayisi
            transfer.bebek_sayisi = bebek_sayisi
            transfer.save()
            
            return redirect('transfer_listesi')
    else:
        form = KullanilacakForm(instance=transfer)
    
    return render(request, 'transfer/transfer_duzenle.html', {'form': form, 'transfer': transfer})

@login_required
def transfer_sil(request, id):
    transfer = get_object_or_404(Transfer, id=id)
    if request.method == 'POST':
        transfer.delete()
        return redirect('transfer_listesi')
    
    return render(request, 'transfer/transfer_sil.html', {'transfer': transfer})

@login_required
def transfer_detay(request, id):
    transfer = get_object_or_404(Transfer, id=id)
    return render(request, 'transfer/transfer_detay.html', {'transfer': transfer})


@login_required
def arac_listesi(request):
    query = request.GET.get('q', '')
    araclar = Arac.objects.all()
    
    if query:
        araclar = araclar.filter(
            Q(plaka__icontains=query) |
            Q(marka__icontains=query) |
            Q(arac_kodu__icontains=query)
        )
        
    return render(request, 'transfer/arac_listesi.html', {'araclar': araclar, 'query': query})

@login_required
def arac_ekle(request):
    if request.method == 'POST':
        form = AracForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('arac_listesi')
    else:
        form = AracForm()
    
    return render(request, 'transfer/arac_ekle.html', {'form': form})

@login_required
def arac_duzenle(request, id):
    arac = get_object_or_404(Arac, id=id)
    if request.method == 'POST':
        form = AracForm(request.POST, instance=arac)
        if form.is_valid():
            form.save()
            return redirect('arac_listesi')
    else:
        form = AracForm(instance=arac)
    
    return render(request, 'transfer/arac_duzenle.html', {'form': form, 'arac': arac})

@login_required
def arac_sil(request, id):
    arac = get_object_or_404(Arac, id=id)
    if request.method == 'POST':
        arac.delete()
        return redirect('arac_listesi')
    
    return render(request, 'transfer/arac_sil.html', {'arac': arac})

@login_required
def arac_detay(request, id):
    arac = get_object_or_404(Arac, id=id)
    return render(request, 'transfer/arac_detay.html', {'arac': arac})


@login_required
def personel_listesi(request):
    query = request.GET.get('q', '')
    personeller = Personel.objects.all()
    
    if query:
        personeller = personeller.filter(
            Q(ad_soyad__icontains=query) |
            Q(telefon__icontains=query)
        )
        
    return render(request, 'transfer/personel_listesi.html', {'personeller': personeller, 'query': query})

@login_required
def personel_ekle(request):
    if request.method == 'POST':
        form = PersonelForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('personel_listesi')
    else:
        form = PersonelForm()
    
    return render(request, 'transfer/personel_ekle.html', {'form': form})

@login_required
def personel_duzenle(request, id):
    personel = get_object_or_404(Personel, id=id)
    if request.method == 'POST':
        form = PersonelForm(request.POST, instance=personel)
        if form.is_valid():
            form.save()
            return redirect('personel_listesi')
    else:
        form = PersonelForm(instance=personel)
    
    return render(request, 'transfer/personel_duzenle.html', {'form': form, 'personel': personel})
    
@login_required
def personel_sil(request, id):
    personel = get_object_or_404(Personel, id=id)
    if request.method == 'POST':
        personel.delete()
        return redirect('personel_listesi')
    
    return render(request, 'transfer/personel_sil.html', {'personel': personel})


@login_required
def masraf_listesi(request):
    masraflar = Masraf.objects.all().order_by('-tarih')
    return render(request, 'transfer/masraf_listesi.html', {'masraflar': masraflar})

@login_required
def masraf_ekle(request):
    if request.method == 'POST':
        # Dosya/Resim yükleneceği için request.FILES parametresi şart!
        form = MasrafForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('masraf_listesi')
    else:
        form = MasrafForm()
    
    return render(request, 'transfer/masraf_ekle.html', {'form': form, 'baslik': 'Yeni Masraf Kaydı Ekle'})

@login_required
def masraf_duzenle(request, id):
    masraf = get_object_or_404(Masraf, id=id)
    if request.method == 'POST':
        form = MasrafForm(request.POST, request.FILES, instance=masraf)
        if form.is_valid():
            form.save()
            return redirect('masraf_listesi')
    else:
        form = MasrafForm(instance=masraf)
    
    return render(request, 'transfer/masraf_duzenle.html', {'form': form, 'masraf': masraf})

@login_required
def masraf_sil(request, id):
    masraf = get_object_or_404(Masraf, id=id)
    if request.method == 'POST':
        masraf.delete()
        return redirect('masraf_listesi')
    
    return render(request, 'transfer/masraf_sil.html', {'masraf': masraf})

@login_required
def masraf_raporu_belge(request):
    masraflar = Masraf.objects.all().order_by('-tarih')
    
    context = {
        'masraflar': masraflar,
    }
    return render(request, 'transfer/masraf_raporu_belge.html', context)

@login_required
def ceza_listesi(request):
    cezalar = Ceza.objects.all().order_by('-tarih')
    return render(request, 'transfer/ceza_listesi.html', {'cezalar': cezalar})

@login_required
def ceza_ekle(request):
    if request.method == 'POST':
        form = CezaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('ceza_listesi')
    else:
        form = CezaForm()
    
    return render(request, 'transfer/ceza_ekle.html', {'form': form, 'baslik': 'Yeni Ceza Kaydı Ekle'})

@login_required
def ceza_duzenle(request, id):
    ceza = get_object_or_404(Ceza, id=id)
    if request.method == 'POST':
        form = CezaForm(request.POST, request.FILES, instance=ceza)
        if form.is_valid():
            form.save()
            return redirect('ceza_listesi')
    else:
        form = CezaForm(instance=ceza)
    
    return render(request, 'transfer/ceza_ekle.html', {'form': form, 'baslik': 'Cezayı Düzenle', 'ceza': ceza}) # Ekleme sayfasıyla aynı tasarımı kullanacağız

@login_required
def ceza_sil(request, id):
    ceza = get_object_or_404(Ceza, id=id)
    if request.method == 'POST':
        ceza.delete()
        return redirect('ceza_listesi')
    return render(request, 'transfer/ceza_sil.html', {'ceza': ceza})


@login_required
def ceza_raporu_belge(request):
    cezalar = Ceza.objects.all().order_by('-tarih')
    
    context = {
        'cezalar': cezalar,
    }
    return render(request, 'transfer/ceza_raporu_belge.html', context)


@login_required
def kiralama_listesi(request):
    kiralamalar = Kiralama.objects.all().order_by('-baslangic_tarihi')
    return render(request, 'transfer/kiralama_listesi.html', {'kiralamalar': kiralamalar})

@login_required
def kiralama_ekle(request):
    if request.method == 'POST':
        form = KiralamaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('kiralama_listesi')
    else:
        form = KiralamaForm()
    
    return render(request, 'transfer/kiralama_duzenle.html', {'form': form, 'baslik': 'Yeni Kiralama Kaydı Oluştur'})

@login_required
def kiralama_duzenle(request, id):
    kiralama = get_object_or_404(Kiralama, id=id)
    if request.method == 'POST':
        form = KiralamaForm(request.POST, instance=kiralama)
        if form.is_valid():
            form.save()
            return redirect('kiralama_listesi')
    else:
        form = KiralamaForm(instance=kiralama)
    
    return render(request, 'transfer/kiralama_duzenle.html', {'form': form, 'baslik': 'Kiralama Kaydını Düzenle', 'kiralama': kiralama})

@login_required
def kiralama_sil(request, id):
    kiralama = get_object_or_404(Kiralama, id=id)
    if request.method == 'POST':
        kiralama.delete()
        return redirect('kiralama_listesi')
    return render(request, 'transfer/kiralama_sil.html', {'kiralama': kiralama})

@login_required
def muhatap_listesi(request):
    query = request.GET.get('q', '')
    muhataplar = Muhatap.objects.all().order_by('unvan')
    if query:
        muhataplar = muhataplar.filter(
            Q(unvan__icontains=query) | Q(vkn__icontains=query) | Q(telefon__icontains=query)
        )
    return render(request, 'transfer/muhatap_listesi.html', {'muhataplar': muhataplar, 'query': query})

@login_required
def muhatap_ekle(request):
    if request.method == 'POST':
        form = MuhatapForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('muhatap_listesi')
    else:
        form = MuhatapForm()
    return render(request, 'transfer/muhatap_ekle.html', {'form': form, 'baslik': 'Yeni Müşteri (Muhatap) Ekle'})

@login_required
def muhatap_duzenle(request, id):
    muhatap = get_object_or_404(Muhatap, id=id)
    if request.method == 'POST':
        form = MuhatapForm(request.POST, instance=muhatap)
        if form.is_valid():
            form.save()
            return redirect('muhatap_listesi')
    else:
        form = MuhatapForm(instance=muhatap)
    return render(request, 'transfer/muhatap_ekle.html', {'form': form, 'baslik': 'Müşteri Bilgilerini Düzenle', 'muhatap': muhatap})

@login_required
def muhatap_sil(request, id):
    muhatap = get_object_or_404(Muhatap, id=id)
    if request.method == 'POST':
        muhatap.delete()
        return redirect('muhatap_listesi')
    return render(request, 'transfer/muhatap_sil.html', {'muhatap': muhatap})

@login_required
def firma_listesi(request):
    firmalar = Firma.objects.all().order_by('ad')
    return render(request, 'transfer/firma_listesi.html', {'firmalar': firmalar})

@login_required
def firma_ekle(request):
    if request.method == 'POST':
        form = FirmaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('firma_listesi')
    else:
        form = FirmaForm()
    return render(request, 'transfer/firma_ekle.html', {'form': form, 'baslik': 'Yeni Şirket Ekle'})

@login_required
def firma_duzenle(request, id):
    firma = get_object_or_404(Firma, id=id)
    if request.method == 'POST':
        form = FirmaForm(request.POST, instance=firma)
        if form.is_valid():
            form.save()
            return redirect('firma_listesi')
    else:
        form = FirmaForm(instance=firma)
    return render(request, 'transfer/firma_ekle.html', {'form': form, 'baslik': 'Şirket Bilgilerini Düzenle', 'firma': firma})

@login_required
def firma_sil(request, id):
    firma = get_object_or_404(Firma, id=id)
    if request.method == 'POST':
        firma.delete()
        return redirect('firma_listesi')
    return render(request, 'transfer/firma_sil.html', {'firma': firma})

@login_required
def arac_turu_listesi(request):
    turler = AracTuru.objects.all()
    # Kilit nokta burası: HTML'in beklediği 'arac_turleri' ismini kullanıyoruz
    return render(request, 'transfer/arac_turu_listesi.html', {'arac_turleri': turler})

@login_required
def arac_turu_ekle(request):
    if request.method == 'POST':
        form = AracTuruForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('arac_turu_listesi')
    else:
        form = AracTuruForm()
    return render(request, 'transfer/arac_turu_ekle.html', {'form': form, 'baslik': 'Yeni Araç Türü Ekle'})

@login_required
def arac_turu_duzenle(request, id):
    tur = get_object_or_404(AracTuru, id=id)
    if request.method == 'POST':
        form = AracTuruForm(request.POST, instance=tur)
        if form.is_valid():
            form.save()
            return redirect('arac_turu_listesi')
    else:
        form = AracTuruForm(instance=tur)
    return render(request, 'transfer/arac_turu_ekle.html', {'form': form, 'baslik': 'Araç Türünü Düzenle', 'tur': tur})

@login_required
def arac_turu_sil(request, id):
    tur = get_object_or_404(AracTuru, id=id)
    if request.method == 'POST':
        tur.delete()
        return redirect('arac_turu_listesi')
    return render(request, 'transfer/arac_turu_sil.html', {'tur': tur})

@login_required
def masraf_turu_listesi(request):
    turler = MasrafTuru.objects.all()
    # Kilit nokta burası: HTML'in beklediği 'masraf_turleri' ismini kullanıyoruz
    return render(request, 'transfer/masraf_turu_listesi.html', {'masraf_turleri': turler})

@login_required
def masraf_turu_ekle(request):
    if request.method == 'POST':
        form = MasrafTuruForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('masraf_turu_listesi')
    else:
        form = MasrafTuruForm()
    return render(request, 'transfer/masraf_turu_ekle.html', {'form': form, 'baslik': 'Yeni Masraf Türü Ekle'})

@login_required
def masraf_turu_duzenle(request, id):
    tur = get_object_or_404(MasrafTuru, id=id)
    if request.method == 'POST':
        form = MasrafTuruForm(request.POST, instance=tur)
        if form.is_valid():
            form.save()
            return redirect('masraf_turu_listesi')
    else:
        form = MasrafTuruForm(instance=tur)
    return render(request, 'transfer/masraf_turu_ekle.html', {'form': form, 'baslik': 'Masraf Türünü Düzenle', 'tur': tur})

@login_required
def masraf_turu_sil(request, id):
    tur = get_object_or_404(MasrafTuru, id=id)
    if request.method == 'POST':
        tur.delete()
        return redirect('masraf_turu_listesi')
    return render(request, 'transfer/masraf_turu_sil.html', {'tur': tur})

@login_required
def get_firma_turleri(request):
    firma_id = request.GET.get('firma_id')
    tur = request.GET.get('tur')
    
    if tur == 'arac':
        if firma_id:
            turler = AracTuru.objects.filter(Q(firma_id=firma_id) | Q(firma__isnull=True))
        else:
            turler = AracTuru.objects.filter(firma__isnull=True)
    elif tur == 'masraf':
        if firma_id:
            turler = MasrafTuru.objects.filter(Q(firma_id=firma_id) | Q(firma__isnull=True))
        else:
            turler = MasrafTuru.objects.filter(firma__isnull=True)
    else:
        turler = []
        
    data = [{'id': t.id, 'tanimi': str(t)} for t in turler]
    return JsonResponse(data, safe=False)

@login_required
def get_arac_details(request, id):
    arac = get_object_or_404(Arac, id=id)
    data = {
        'plaka': arac.plaka,
        'marka': arac.marka or "Belirtilmedi",
        'model': arac.model_tanim or "Belirtilmedi",
        'kapasite': arac.kapasite,
        'vites': arac.get_vites_display() if arac.vites else "Belirtilmedi",
        'yakit': arac.get_yakit_tipi_display() if arac.yakit_tipi else "Belirtilmedi",
        'durum': arac.get_arac_durumu_display(),
        'segment': arac.segment or "Standart",
        'firma_id': arac.firma.id if arac.firma else None
    }
    return JsonResponse(data)

@login_required
def sefer_listesi(request):
    # Aktif şoförleri ve onlara atanmış, henüz tamamlanmamış veya iptal edilmemiş transferleri çekelim
    personeller = Personel.objects.filter(aktif_mi=True).prefetch_related('transfer_set')
    
    # Tüm transferleri şoför bazlı gruplayarak gönderelim
    # (Not: Transfer modelinde personel alanı ForeignKey olduğu için ters ilişki transfer_set üzerinden gelir)
    return render(request, 'transfer/sefer_listesi.html', {'personeller': personeller})

@login_required
def sefer_raporu_belge(request, personel_id):
    # Tıklanan şoförü bul
    personel = get_object_or_404(Personel, id=personel_id)
    # Sadece o şoföre ait seferleri al
    seferler = personel.transfer_set.all().order_by('alis_saati')
    
    context = {
        'personel': personel,
        'seferler': seferler,
    }
    return render(request, 'transfer/sefer_raporu_belge.html', context)

@login_required
def transfer_durum_guncelle(request, id, yeni_durum):
    transfer = get_object_or_404(Transfer, id=id)
    transfer.transfer_durumu = yeni_durum
    
    # Eğer transfer tamamlandıysa aracın durumunu da boşa çıkarabiliriz (Opsiyonel)
    if yeni_durum == 'tamamlandi' and transfer.arac_kodu:
        transfer.arac_kodu.arac_durumu = 'bosta'
        transfer.arac_kodu.save()
        
    transfer.save()
    return redirect('sefer_listesi')


@login_required
def get_müsait_araclar(request):
    """
    Seçilen tarih aralığında müsait olan araçları döndüren AJAX view.
    """
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    exclude_transfer_id = request.GET.get('exclude')

    if not start_str or not end_str:
        return JsonResponse({'error': 'Tarih bilgisi eksik'}, status=400)

    try:
        start_time = parse_datetime(start_str)
        end_time = parse_datetime(end_str)
        
        # Eğer timezone unaware ise aware yapalım (Django default ayarlarına göre)
        if start_time and timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time)
        if end_time and timezone.is_naive(end_time):
            end_time = timezone.make_aware(end_time)
            
    except Exception:
        return JsonResponse({'error': 'Tarih formatı geçersiz'}, status=400)

    if not start_time or not end_time:
        return JsonResponse({'error': 'Tarih formatı geçersiz'}, status=400)

    # Elimizdeki tüm araçları çekiyoruz
    tum_araclar = Arac.objects.all()
    müsait_araclar = []

    for arac in tum_araclar:
        if arac.is_available(start_time, end_time, exclude_transfer_id=exclude_transfer_id):
            müsait_araclar.append({
                'id': arac.id,
                'plaka': arac.plaka,
                'marka': arac.marka or "",
                'model': arac.model_tanim or "",
                'kapasite': arac.kapasite,
                'durum': arac.get_arac_durumu_display()
            })

    return JsonResponse({'araclar': müsait_araclar})


@login_required
def get_musait_personeller(request):
    """
    Seçilen tarih aralığında müsait olan personelleri (şoförleri) döndüren AJAX view.
    """
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    exclude_transfer_id = request.GET.get('exclude')

    if not start_str or not end_str:
        return JsonResponse({'error': 'Tarih bilgisi eksik'}, status=400)

    try:
        start_time = parse_datetime(start_str)
        end_time = parse_datetime(end_str)
        if start_time and timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time)
        if end_time and timezone.is_naive(end_time):
            end_time = timezone.make_aware(end_time)
    except Exception:
        return JsonResponse({'error': 'Tarih formatı geçersiz'}, status=400)

    if not start_time or not end_time:
        return JsonResponse({'error': 'Tarih formatı geçersiz'}, status=400)

    tum_personeller = Personel.objects.filter(aktif_mi=True)
    musait_personeller = []

    for personel in tum_personeller:
        if personel.is_available(start_time, end_time, exclude_transfer_id=exclude_transfer_id):
            musait_personeller.append({
                'id': personel.id,
                'ad_soyad': str(personel),
                'gorev': personel.gorevi or "Şoför"
            })

    return JsonResponse({'personeller': musait_personeller})


@login_required
def get_arac_mesgul_tarihler(request):
    """
    Seçili aracın meşgul olduğu tarih aralıklarını döndürür (Flatpickr disable listesi için).
    """
    arac_id = request.GET.get('arac_id')
    exclude_transfer_id = request.GET.get('exclude')

    if not arac_id:
        return JsonResponse({'mesgul_tarihler': []})

    try:
        arac = Arac.objects.get(id=arac_id)
    except Arac.DoesNotExist:
        return JsonResponse({'mesgul_tarihler': []})

    from django.db.models import Q
    qs = Transfer.objects.filter(
        arac_kodu=arac,
        transfer_durumu__in=['beklemede', 'basladi']
    ).exclude(
        varis_saati__isnull=True
    )

    if exclude_transfer_id:
        try:
            qs = qs.exclude(id=int(exclude_transfer_id))
        except (ValueError, TypeError):
            pass

    mesgul = []
    for t in qs:
        if t.alis_saati and t.varis_saati:
            mesgul.append({
                'start': t.alis_saati.strftime('%Y-%m-%dT%H:%M'),
                'end':   t.varis_saati.strftime('%Y-%m-%dT%H:%M'),
                'label': f'Transfer #{t.id}',
            })

    return JsonResponse({'mesgul_tarihler': mesgul})


@login_required
def get_personel_mesgul_tarihler(request):
    """
    Seçili şoförün meşgul olduğu tarih aralıklarını döndürür (Flatpickr disable listesi için).
    """
    personel_id = request.GET.get('personel_id')
    exclude_transfer_id = request.GET.get('exclude')

    if not personel_id:
        return JsonResponse({'mesgul_tarihler': []})

    try:
        personel = Personel.objects.get(id=personel_id)
    except Personel.DoesNotExist:
        return JsonResponse({'mesgul_tarihler': []})

    from django.db.models import Q
    qs = Transfer.objects.filter(
        personel=personel,
        transfer_durumu__in=['beklemede', 'basladi']
    ).exclude(
        varis_saati__isnull=True
    )

    if exclude_transfer_id:
        try:
            qs = qs.exclude(id=int(exclude_transfer_id))
        except (ValueError, TypeError):
            pass

    mesgul = []
    for t in qs:
        if t.alis_saati and t.varis_saati:
            mesgul.append({
                'start': t.alis_saati.strftime('%Y-%m-%dT%H:%M'),
                'end':   t.varis_saati.strftime('%Y-%m-%dT%H:%M'),
                'label': f'Transfer #{t.id}',
            })

    return JsonResponse({'mesgul_tarihler': mesgul})

@login_required
def raporlar_ana(request):
    return render(request, 'transfer/raporlar_ana.html')

@login_required
def arac_raporu(request):
    araclar = Arac.objects.all()
    rapor_verisi = []
    
    for arac in araclar:
        # Aracın toplam masrafını hesapla (Kayıt yoksa 0 ata)
        masraf_toplam = Masraf.objects.filter(arac=arac).aggregate(toplam=Sum('tutar'))['toplam'] or 0
        
        # Aracın toplam cezasını hesapla (Kayıt yoksa 0 ata)
        ceza_toplam = Ceza.objects.filter(arac=arac).aggregate(toplam=Sum('tutar'))['toplam'] or 0
        
        # Models.py'da yazdığın o harika "current_availability" özelliğini kullanıyoruz
        musait_mi = arac.current_availability
        
        rapor_verisi.append({
            'arac': arac,
            'masraf_toplam': masraf_toplam,
            'ceza_toplam': ceza_toplam,
            'musait_mi': musait_mi,
        })
        
    context = {
        'rapor_verisi': rapor_verisi,
        'toplam_arac': araclar.count(),
        'musait_arac': sum(1 for r in rapor_verisi if r['musait_mi']),
        'mesgul_arac': sum(1 for r in rapor_verisi if not r['musait_mi']),
    }
    
    return render(request, 'transfer/arac_raporu.html', context)

@login_required
def transfer_raporu(request):
    transferler = Transfer.objects.all().order_by('-alis_saati')
    
    # İstatistikleri hesapla
    toplam_transfer = transferler.count()
    tamamlanan_transfer = transferler.filter(transfer_durumu='tamamlandi').count()
    bekleyen_transfer = transferler.filter(transfer_durumu__in=['beklemede', 'basladi']).count()
    
    # Toplam Gelir ve Tahsil Edilen/Bekleyen Tutarlar
    toplam_gelir = transferler.aggregate(toplam=Sum('tutar'))['toplam'] or 0
    tahsil_edilen = transferler.filter(odendi_mi=True).aggregate(toplam=Sum('tutar'))['toplam'] or 0
    bekleyen_tahsilat = toplam_gelir - tahsil_edilen
    
    context = {
        'transferler': transferler,
        'toplam_transfer': toplam_transfer,
        'tamamlanan_transfer': tamamlanan_transfer,
        'bekleyen_transfer': bekleyen_transfer,
        'toplam_gelir': toplam_gelir,
        'tahsil_edilen': tahsil_edilen,
        'bekleyen_tahsilat': bekleyen_tahsilat,
    }
    
    return render(request, 'transfer/transfer_raporu.html', context)

@login_required
def masraf_raporu(request):
    # Tüm masrafları tarihe göre en yeniden eskiye sıralıyoruz
    masraflar = Masraf.objects.all().select_related('arac', 'masraf_turu', 'personel').order_by('-tarih')
    
    # Genel Özet İstatistikler
    toplam_tutar = masraflar.aggregate(toplam=Sum('tutar'))['toplam'] or 0
    islem_sayisi = masraflar.count()
    
    # En çok para harcanan masraf türünü bulma (Örn: Yakıt)
    en_cok_harcanan = masraflar.values('masraf_turu__tanimi').annotate(toplam=Sum('tutar')).order_by('-toplam').first()
    
    en_masrafli_tur_adi = en_cok_harcanan['masraf_turu__tanimi'] if en_cok_harcanan and en_cok_harcanan['masraf_turu__tanimi'] else "Henüz Veri Yok"
    en_masrafli_tur_tutari = en_cok_harcanan['toplam'] if en_cok_harcanan else 0

    context = {
        'masraflar': masraflar,
        'toplam_tutar': toplam_tutar,
        'islem_sayisi': islem_sayisi,
        'en_masrafli_tur_adi': en_masrafli_tur_adi,
        'en_masrafli_tur_tutari': en_masrafli_tur_tutari,
    }
    
    return render(request, 'transfer/masraf_raporu.html', context)

@login_required
def ceza_raporu(request):
    # Tüm cezaları tarihe göre en yeniden eskiye sıralıyoruz
    cezalar = Ceza.objects.all().select_related('arac', 'personel').order_by('-tarih')
    
    # Genel Özet İstatistikler
    toplam_ceza_tutari = cezalar.aggregate(toplam=Sum('tutar'))['toplam'] or 0
    odenen_ceza = cezalar.filter(odendi_mi=True).aggregate(toplam=Sum('tutar'))['toplam'] or 0
    odenmeyen_ceza = toplam_ceza_tutari - odenen_ceza
    
    # Ceza Sayıları
    toplam_ceza_sayisi = cezalar.count()
    odenmeyen_sayisi = cezalar.filter(odendi_mi=False).count()

    context = {
        'cezalar': cezalar,
        'toplam_ceza_tutari': toplam_ceza_tutari,
        'odenen_ceza': odenen_ceza,
        'odenmeyen_ceza': odenmeyen_ceza,
        'toplam_ceza_sayisi': toplam_ceza_sayisi,
        'odenmeyen_sayisi': odenmeyen_sayisi,
    }
    
    return render(request, 'transfer/ceza_raporu.html', context)

@login_required
def kiralama_raporu(request):
    # Tüm kiralamaları başlangıç tarihine göre yeniden eskiye sıralıyoruz
    kiralamalar = Kiralama.objects.all().select_related('arac').order_by('-baslangic_tarihi')
    
    # Genel Özet İstatistikler
    toplam_kiralama_sayisi = kiralamalar.count()
    toplam_beklenen_gelir = kiralamalar.aggregate(toplam=Sum('toplam_tutar'))['toplam'] or 0
    
    # Sözleşme Durumları
    sozlesmesi_tamam_sayisi = kiralamalar.filter(sozlesme_imzalandi=True).count()
    sozlesme_bekleyen_sayisi = kiralamalar.filter(sozlesme_imzalandi=False).count()

    context = {
        'kiralamalar': kiralamalar,
        'toplam_kiralama_sayisi': toplam_kiralama_sayisi,
        'toplam_beklenen_gelir': toplam_beklenen_gelir,
        'sozlesmesi_tamam_sayisi': sozlesmesi_tamam_sayisi,
        'sozlesme_bekleyen_sayisi': sozlesme_bekleyen_sayisi,
    }
    
    return render(request, 'transfer/kiralama_raporu.html', context)


@login_required
def sigorta_listesi(request):
    sigortalar = Sigorta.objects.all().select_related('arac').order_by('-police_bitis_tarihi')
    return render(request, 'transfer/sigorta_listesi.html', {'sigortalar': sigortalar})

@login_required
def sigorta_ekle(request):
    if request.method == 'POST':
        form = SigortaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('sigorta_listesi')
    else:
        form = SigortaForm()
    return render(request, 'transfer/sigorta_ekle.html', {'form': form, 'baslik': 'Yeni Sigorta Ekle'})

@login_required
def sigorta_duzenle(request, id):
    sigorta = get_object_or_404(Sigorta, id=id)
    if request.method == 'POST':
        form = SigortaForm(request.POST, instance=sigorta)
        if form.is_valid():
            form.save()
            return redirect('sigorta_listesi')
    else:
        form = SigortaForm(instance=sigorta)
    return render(request, 'transfer/sigorta_ekle.html', {'form': form, 'baslik': 'Sigortayı Düzenle', 'sigorta': sigorta})

@login_required
def sigorta_sil(request, id):
    sigorta = get_object_or_404(Sigorta, id=id)
    if request.method == 'POST':
        sigorta.delete()
        return redirect('sigorta_listesi')
    return render(request, 'transfer/sigorta_sil.html', {'sigorta': sigorta})



@login_required
def hatirlatma_raporu(request):
    bugun = date.today()
    
    araclar = Arac.objects.prefetch_related(
        Prefetch('sigortalar', queryset=Sigorta.objects.order_by('-police_bitis_tarihi'))
    ).all()

    uyari_listesi = []
    gecmis_sayisi = 0
    yaklasan_sayisi = 0

    for arac in araclar:
        # 1. Muayene Kontrolü
        if arac.muayene_tarihi:
            kalan_gun = (arac.muayene_tarihi - bugun).days
            if kalan_gun < 0:
                uyari_listesi.append({'arac': arac, 'tur': 'TÜVTÜRK Muayene', 'sirket': '-', 'police_no': '-', 'tarih': arac.muayene_tarihi, 'durum': 'Gecmis', 'kalan': kalan_gun})
                gecmis_sayisi += 1
            elif kalan_gun <= 30:
                uyari_listesi.append({'arac': arac, 'tur': 'TÜVTÜRK Muayene', 'sirket': '-', 'police_no': '-', 'tarih': arac.muayene_tarihi, 'durum': 'Yaklasiyor', 'kalan': kalan_gun})
                yaklasan_sayisi += 1

        # 2. Egzoz Emisyon Kontrolü
        if arac.egzoz_emisyon_tarihi:
            kalan_gun = (arac.egzoz_emisyon_tarihi - bugun).days
            if kalan_gun < 0:
                uyari_listesi.append({'arac': arac, 'tur': 'Egzoz Emisyon', 'sirket': '-', 'police_no': '-', 'tarih': arac.egzoz_emisyon_tarihi, 'durum': 'Gecmis', 'kalan': kalan_gun})
                gecmis_sayisi += 1
            elif kalan_gun <= 30:
                uyari_listesi.append({'arac': arac, 'tur': 'Egzoz Emisyon', 'sirket': '-', 'police_no': '-', 'tarih': arac.egzoz_emisyon_tarihi, 'durum': 'Yaklasiyor', 'kalan': kalan_gun})
                yaklasan_sayisi += 1

        # 3. Sigorta Poliçesi Kontrolü
        son_sigorta = arac.sigortalar.first()
        if son_sigorta and son_sigorta.police_bitis_tarihi:
            kalan_gun = (son_sigorta.police_bitis_tarihi - bugun).days
            
            # Artık birleştirmiyoruz, ayrı ayrı değişkenlere alıyoruz
            sirket_adi = son_sigorta.sigorta_sirketi if son_sigorta.sigorta_sirketi else "Belirtilmemiş"
            police_no = son_sigorta.police_no if son_sigorta.police_no else "Belirtilmemiş"
            
            if kalan_gun < 0:
                uyari_listesi.append({'arac': arac, 'tur': son_sigorta.get_sigorta_turu_display(), 'sirket': sirket_adi, 'police_no': police_no, 'tarih': son_sigorta.police_bitis_tarihi, 'durum': 'Gecmis', 'kalan': kalan_gun})
                gecmis_sayisi += 1
            elif kalan_gun <= 30:
                uyari_listesi.append({'arac': arac, 'tur': son_sigorta.get_sigorta_turu_display(), 'sirket': sirket_adi, 'police_no': police_no, 'tarih': son_sigorta.police_bitis_tarihi, 'durum': 'Yaklasiyor', 'kalan': kalan_gun})
                yaklasan_sayisi += 1

    uyari_listesi.sort(key=lambda x: x['kalan'])

    context = {
        'uyari_listesi': uyari_listesi,
        'gecmis_sayisi': gecmis_sayisi,
        'yaklasan_sayisi': yaklasan_sayisi,
        'sorunsuz_arac_sayisi': araclar.count() - len(set([u['arac'].id for u in uyari_listesi]))
    }
    
    return render(request, 'transfer/hatirlatma_raporu.html', context)