from django.shortcuts import redirect
from django.urls import resolve

class CustomerAccessMiddleware:
    """
    Personel olmayan (Müşteri) kullanıcıların URL üzerinden admin sayfalarına girmesini engeller.
    Müşterilerin sadece izin verilen sayfalarda gezinmesini sağlar.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_staff:
            allowed_url_names = [
                'transfer_ekle',
                'transfer_listesi',
                'transfer_duzenle',
                'transfer_detay',
                'transfer_sil',
                'kayit_ol',
                'giris_yap',
                'cikis_yap',
                # Formdaki AJAX sorguları için izinler
                'musait_araclar',
                'musait_personeller',
                'arac_mesgul_tarihler',
                'personel_mesgul_tarihler',
                'get_arac_details',
                'get_firma_turleri',
            ]
            
            try:
                current = resolve(request.path_info)
                # Eğer Django admin sayfasına girmeye çalışıyorsa
                if current.app_name == 'admin':
                    return redirect('transfer_listesi')
                    
                # Eğer URL'in ismi izin verilenler listesinde değilse
                if current.url_name and current.url_name not in allowed_url_names:
                    return redirect('transfer_listesi')
            except Exception:
                pass
                
        response = self.get_response(request)
        return response
