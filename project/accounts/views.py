from urllib import request

from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.shortcuts import render, redirect, get_object_or_404
from django.core.cache import cache
from django.core.paginator import Paginator

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LogoutView
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse, Http404, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.db.models import Q

import secrets
import pickle


import re
from difflib import SequenceMatcher

from utils.throttle import check_throttle
from utils.email_sms import send_email_sms
from utils.password_policy import password_change_policy
from utils.verify_otp import verify_otp
from crud.user import user_crud

from accounts.models import CustomUser
from accounts.form import (
    CustomUserCreationForm,
    EmailVerifyForm,
    VerifyCodeForm,
)
from accounts.form_profile import ProfileForm

from properties.models import (
    Property,
    Reservation,
    PropertyAmenity,
    Amenity,
    City,
    Area,
    Village,
    PropertyImage,
    
    
    Review,
)
from properties.forms import PropertyForm, PropertyImageForm,PropertyUpdateForm, ReviewForm
from crud.property import property_crud

class DashboardIndexView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'


    def get_total_views(self,batch_size=5000):
        # redis_client = cache.client.get_client(write=False)
        #
        total_views = 0
        # batch = []
        #
        # for key in redis_client.scan_iter(match="*:property-detail-*", count=batch_size):
        #     batch.append(key)
        #     if len(batch) >= batch_size:
        #         values = redis_client.mget(batch)
        #         for v in values:
        #             if v:
        #                 try:
        #                     total_views += int(v)
        #                 except (ValueError, TypeError):
        #                     pass
        #         batch = []
        #
        # if batch:
        #     values = redis_client.mget(batch)
        #     for v in values:
        #         if v:
        #             try:
        #                 total_views += int(v)
        #             except (ValueError, TypeError):
        #                 pass
        #
        # cache.set("total_property_views", total_views, timeout=None)
        return total_views


    def dispatch(self, request, *args, **kwargs):
        super().dispatch(request, *args, **kwargs)

        if not request.user.is_authenticated:
            return redirect('login-admin')
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['total_properties'] = Property.objects.count()
        
        context['total_reviews'] = Review.objects.count()

        context['total_views'] = self.get_total_views()

        return context
    

# "Add new" page


class PropertyCreateView(LoginRequiredMixin, CreateView):
    model = Property
    form_class = PropertyForm
    template_name = 'dashboard-add-new-property.html'
    success_url = reverse_lazy('property_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Existing city context
        context['cities'] = City.objects.all().order_by('name')
        if 'image_form' not in kwargs:
            context['image_form'] = PropertyImageForm()
        return context

    def post(self, request, *args, **kwargs):
        # MÜTLƏQ: post metodu başladıqda obyektin hələ yaranmadığını bildiririk
        self.object = None
        
        form = self.get_form()
        image_form = PropertyImageForm(request.POST, request.FILES)

        if form.is_valid() and image_form.is_valid():
            return self.form_valid(form, image_form)
        return self.form_invalid(form, image_form)

    def form_valid(self, form, image_form):
        images = image_form.cleaned_data.get('images') or []

        # 1-ci şəkil -> cover, Property.image sahəsində saxlanılır
        if images:
            form.instance.image = images[0]

        self.object = form.save()

        # Qalan şəkillər -> PropertyImage-də saxlanılır
        for img in images[1:]:
            PropertyImage.objects.create(prop=self.object, image=img)

        # Clear and re-save amenities relation
        PropertyAmenity.objects.filter(prop=self.object).delete()
        for amenity in form.cleaned_data.get('amenities', []):
            PropertyAmenity.objects.create(prop=self.object, amenity=amenity)

        return redirect(self.get_success_url())

    def form_invalid(self, form, image_form):
        # SIĞORTA: form_invalid daxilində də obyektin None olmasını təmin edirik
        self.object = None
        return self.render_to_response(
            self.get_context_data(form=form, image_form=image_form)
        )

def get_areas(request):
    city_id = request.GET.get('city_id')
    areas = Area.objects.filter(city_id=city_id).values('id', 'name').order_by('name')
    return JsonResponse(list(areas), safe=False)

def get_villages(request):
    area_id = request.GET.get('area_id')
    villages = Village.objects.filter(area_id=area_id).values('id', 'name').order_by('name')
    return JsonResponse(list(villages), safe=False)
    

@require_POST
def amenity_add_ajax(request):
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'Ad daxil edilməyib.'}, status=400)

    amenity, created = Amenity.objects.get_or_create(name=name)
    return JsonResponse({'id': amenity.pk, 'name': amenity.name, 'created': created})



# "My Reservation" page
class ReservationDeleteView(LoginRequiredMixin, DeleteView):
    model = Reservation
    success_url = reverse_lazy('my_reservations') 

    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

        
class ReservationListView(LoginRequiredMixin, ListView): 
    model = Reservation
    template_name = 'my-reservations.html'
    context_object_name = 'reservations'
    paginate_by = 5  # Defolt olaraq hər səhifədə 5 rezervasiya göstəriləcək

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        query = self.request.GET.get('q')
        if query:
            query = query.strip()
            queryset = queryset.filter(
                Q(name__icontains=query) | Q(surname__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        # 1. Mövcud context məlumatlarını götürürük (page_obj və paginator buradadır)
        context = super().get_context_data(**kwargs)
        
        paginator = context.get('paginator')
        page_obj = context.get('page_obj')
        
        if paginator and page_obj:
            # 2. Modern HTML şablonundakı ellipsli (...) nömrələmə diapazonunu bura ötürürük
            context['custom_page_range'] = paginator.get_elided_page_range(
                number=page_obj.number,
                on_each_side=2,
                on_ends=1
            )
        
        # 3. Axtarış ("q" parametri) edildikdən sonra digər səhifələrə keçəndə axtarışın itməməsi üçün
        query_params = self.request.GET.copy()
        query_params.pop('page', None)  # page parametrini silirik ki, dublikat olmasın
        context['query_string'] = query_params.urlencode()
        
        return context
        




# 2. Edit
@login_required
def dashboard_properties(request):
    properties = (
    Property.objects
    .select_related(
        'category',
        'city',
        'area',
        'village',
    ).all()
    )
    # Əgər elanlar user-ə bağlıdırsa bunu aç:
    # properties = properties.filter(user=request.user)

    search = request.GET.get('search', '').strip()
    if search:
        properties = properties.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(category__name__icontains=search) |
            Q(city__name__icontains=search) |
            Q(area__name__icontains=search) |
            Q(village__name__icontains=search)
        )

    sort_by = request.GET.get('sort_by', '')

    if sort_by == 'name_asc':
        properties = properties.order_by('name')
    elif sort_by == 'price_asc':
        properties = properties.order_by('price')
    elif sort_by == 'price_desc':
        properties = properties.order_by('-price')
    elif sort_by == 'oldest':
        properties = properties.order_by('created_at')
    elif sort_by == 'newest':
        properties = properties.order_by('-created_at')
    else:
        properties = properties.order_by('-created_at')

    paginator = Paginator(properties, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    custom_page_range = paginator.get_elided_page_range(
        number=page_obj.number,
        on_each_side=2,
        on_ends=1,
    )

    query_params = request.GET.copy()
    query_params.pop('page', None)

    context = {
        'properties': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'custom_page_range': custom_page_range,
        'current_filters': request.GET,
        'query_string': query_params.urlencode(),
    }

    return render(request, 'dashboard-my-properties.html', context)


#My Reviews
@login_required
def dashboard_reviews(request):
    current_tab = request.GET.get('tab', 'approved')
    
    approved_count = Review.objects.filter(is_allowed=True).count()
    pending_count = Review.objects.filter(is_allowed=False).count()
    
    # Seçilən taba görə filterləmə edirik
    if current_tab == 'pending':
        reviews_list = Review.objects.filter(is_allowed=False).order_by('-created_at')
    else:
        reviews_list = Review.objects.filter(is_allowed=True).order_by('-created_at')
        current_tab = 'approved'

    # Səhifələmə: Hər səhifədə neçə rəy görünsün? (Məsələn: 5 rəy)
    paginator = Paginator(reviews_list, 5)
    page_number = request.GET.get('page')
    reviews = paginator.get_page(page_number)

    context = {
        'reviews': reviews,
        'current_tab': current_tab,
        'approved_count': approved_count,
        'pending_count': pending_count,
    }





    # reviews = Review.objects.order_by('-created_at')
    
    # context = {
    #     'reviews': reviews,
    #     'pending_count': reviews.filter(is_allowed=False).count(),
    #     'approved_count': reviews.filter(is_allowed=True).count(),
    # }
    return render(request, 'dashboard-reviews.html', context)


@login_required
def toggle_review(request, review_id):
    """Owner öz property-sinə gələn rəyi təsdiqləyir / gizlədir."""
    review = get_object_or_404(Review, id=review_id)

    review.is_allowed = not review.is_allowed
    review.save(update_fields=['is_allowed'])
    messages.success(request, 'Rəyin statusu yeniləndi.')
    return redirect('dashboard-reviews')


@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.delete()
    messages.success(request, 'Rəy silindi.')
    return redirect('dashboard-reviews')
# _------------------------------------------------------------


class PropertyUpdateView(LoginRequiredMixin, UpdateView):
    model = Property
    form_class = PropertyUpdateForm
    template_name = 'dashboard-property-edit.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    success_url = reverse_lazy('dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['all_amenities'] = Amenity.objects.order_by('name')
        context['selected_amenity_ids'] = list(
            PropertyAmenity.objects.filter(prop=self.object).values_list('amenity_id', flat=True)
        )
        return context

    def form_valid(self, form):
        property = form.save(commit=False)

        changed_fields = form.changed_data
        if changed_fields:
            property.save(update_fields=changed_fields)
        else:
            property.save()

        # --- Amenities ---
        selected_ids = self.request.POST.getlist('amenities')
        PropertyAmenity.objects.filter(prop=property).delete()
        if selected_ids:
            PropertyAmenity.objects.bulk_create([
                PropertyAmenity(prop=property, amenity_id=aid)
                for aid in selected_ids
            ])

        # --- Qalereya: yalnız Save basılanda tətbiq olunur ---
        deleted_ids = self.request.POST.getlist('deleted_images')
        if deleted_ids:
            images_to_delete = PropertyImage.objects.filter(prop=property, id__in=deleted_ids)
            for img in images_to_delete:
                img.image.delete(save=False)  # faylı storage-dan da sil
            images_to_delete.delete()

        new_images = self.request.FILES.getlist('images')
        if new_images:
            PropertyImage.objects.bulk_create([
                PropertyImage(prop=property, image=img)
                for img in new_images
            ])

        return redirect(self.success_url)


# 3. Delete

def property_delete_view(request, pk):
    if not request.user.is_authenticated:
        return redirect('login-admin')
    
    property_obj = get_object_or_404(Property, pk=pk)
    delete = property_crud.delete(db_obj=property_obj)

    if delete:
        messages.success(request, "Mülk uğurla silindi.")
        return redirect('my_properties')
    
    messages.error(request, "Mülkü silmək mümkün olmadı.")
    return redirect('my_properties') 


class UserProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = 'dashboard-my-profiles.html'
    success_url = reverse_lazy('my_profile')

    def get_object(self, queryset=None):
        return self.request.user


class UserLogoutView(LogoutView):
    next_page = 'home'


from logger.base import BaseLogger
from logger.view_logger import ViewLogger
logger = BaseLogger(name="AUTH",db_log=True)
#Login User
@csrf_protect
def login_view(request):
    logger1 = ViewLogger.from_request(request, view_name="owner_detail",db_log=True)
    logger1.request_started()

    template_name = 'auth/login.html'
    if request.user.is_authenticated:
        return redirect('my-profile')

    if check_throttle(request,
            endpoint='login',
            limit=5,
            timeout=60,
            block_time=300):
        return render(request, f'{template_name}', {
            'error': '5 dəqiqə bloklandınız.'
        })

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not email or not password:
            try:
                x = 10 / 0
            except Exception as e:
                logger.exception(
                    "Hesablama zamanı xəta baş verdi",
                    exc=e,
                    user_id=15,
                )
            logger.warning(
                "Login validation failed",
                email=email,
                password=password,
                ip=request.META.get("REMOTE_ADDR"),
            )
            return render(request, 'auth/login.html', {
                'error': 'Email və şifrənizi daxil edin.'
            })

        user = authenticate(request, username=email, password=password)

        if user is not None:

            logger.success(
                "User logged in",
                user_id=user.id,
                email=user.email,
            )
            login(request, user)
            return redirect('my-profile')
        else:
            return render(request, 'auth/login.html', {
                'error': 'Email və ya şifrə yanlışdır.'
            })

    return render(request, 'auth/login.html')



def email_verification_view(request):
    template_name = 'auth/email_verification.html'

    if check_throttle(
        request,
        endpoint='forgot_password',
        limit=15,
        timeout=60,
        block_time=300
    ):
        return render(request, template_name, {
            'error': '5 dəqiqə bloklandınız.'
        })
    form = EmailVerifyForm(request.POST)

    if request.method == 'POST':
        step = request.POST.get('step')

        if step == 'send_code':
            form = EmailVerifyForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data.get('email')
                if not email:
                    return render(request, template_name, {
                        'form': form,
                        'error': 'E-maili daxil edin!'
                    })

                user = user_crud.get_by_email(email=email)
                if not user:
                    return render(request, template_name, {
                        "form": form,
                        'error': 'Daxil etdiniz email səhvdir!'
                    })

                if not password_change_policy.get_password_change_count_today(user=user):
                    return render(request, template_name, {
                        "form": form,
                        'error': 'Gün ərzində parol dəyişmə limiti keçib. 24 saatdan yeniden yoxlayın!'
                    })

                result  = send_email_sms(request, email_type='forgot_password', account=user)

                verify_form = VerifyCodeForm(
                    initial={
                        "email": email
                    }
                )

                if not result["status"]:
                    return render(request, template_name, {
                        "form": verify_form,
                        "code_sent": True,
                        "email": email,
                        "error": result["message"],
                    })

                return render(request, template_name, {
                    "form": verify_form,
                    "code_sent": True,
                    "email": email,
                    "message": result["message"],
                })

            return render(request, template_name, {
                "form": form
            })

        if step == 'verify_code':
            email = request.POST.get("email")

            form = VerifyCodeForm(
                request.POST,
                initial={"email": email}
            )
            if form.is_valid():
                code = "".join([
                    form.cleaned_data["code_1"],
                    form.cleaned_data["code_2"],
                    form.cleaned_data["code_3"],
                    form.cleaned_data["code_4"],
                    form.cleaned_data["code_5"],
                    form.cleaned_data["code_6"],
                ])

                if code != verify_otp(email=email,code=str(code)):
                    return render(request, template_name, {
                        "form": form,
                        "code_sent": True,
                        "email": email,
                        "error": "Daxil edilmis Kod sehvdir."
                    })
                user = user_crud.get_by_email(email=email)
                cache.delete(f"otp:{user.email}")

                reset_token = secrets.token_urlsafe(32)
                request.session['reset_username'] = user.username
                request.session['reset_token'] = reset_token

                cache.set(
                    f"reset_token:{user.username}",
                    reset_token,
                    timeout=120
                )
                return redirect('accounts:reset-password')

            return render(request, template_name, {
                "form": form,
                "code_sent": True,
                "email": email
            })

    return render(request, template_name,{"form": form})



def reset_password_view(request):
    template_name = 'auth/reset_password.html'

    session_username  = request.session.get('reset_username')
    session_token  = request.session.get('reset_token')

    cached_token= cache.get(f"reset_token:{session_username }")

    if (
            not session_username
            or not session_token
            or not cached_token
            or session_token != cached_token
    ):
        raise Http404

    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        user = user_crud.get_by_username(username=session_username)
        if not user:
            return render(request, template_name, {
                "error": "Belə bir istifadəçi mövcud deyil!"
            })

        if password != confirm_password:
            return render(request, template_name, {
                "error": "Daxil edilmiş parol eyni deyildir."
            })

        try:
            password_change_policy.validate_password_policy(password=password)
        except ValueError as e:
            return render(request, template_name, {
                "error": str(e),
            })

        if password_change_policy.update_password(user=user, password=password):
            cache.delete(f"reset_token:{session_username}")
            request.session.pop('reset_username', None)
            request.session.pop('reset_token', None)

            messages.success(request, 'Parol uğurla dəyişdirildi.')
            return redirect('accounts:login-admin')



    return render(request, 'auth/reset_password.html')


def logout_view(request):
    logout(request)
    return redirect('index')


def my_profile_view(request):
    template_name = 'dashboard-my-profiles.html'
    if not request.user.is_authenticated:
        return redirect('login-admin')

    user = request.user
    email = request.user.email
    if not user:
        return redirect('login-admin')

    if request.method == 'POST':
        form = ProfileForm(
            request.POST,
            request.FILES,
            instance=user
        )

        if form.is_valid():
            user = form.save(commit=False)
            changed_data = {
                field: form.cleaned_data[field]
                for field in form.changed_data
                if field not in {
                    "old_password",
                    "new_password",
                    "confirm_new_password",
                }
            }

            old_password = form.cleaned_data.get("old_password")
            new_password = form.cleaned_data.get("new_password")
            confirm_password = form.cleaned_data.get("confirm_new_password")

            if bool(old_password) and bool(new_password):
                if not password_change_policy.get_password_change_count_today(user=user):
                    return render(request, template_name, {
                        "form": form,
                        'error': 'Gün ərzində parol dəyişmə limiti keçib. 24 saatdan yeniden yoxlayın!'
                    })

                if not user.check_password(old_password):
                    return render(request, template_name, {
                        "form": form,
                        'error': 'Daxil edilmiş parol düzgün deyildir!'
                    })

                if new_password != confirm_password:
                    return render(request, template_name, {
                        "form": form,
                        'error': "Parollar eyni deyil."
                    })

                try:
                    password_change_policy.validate_password_policy(password=new_password)
                except ValueError as e:
                    return render(request, template_name, {
                        'form': form,
                        "error": str(e),
                    })

                password_change_policy.update_password(user=user, password=new_password)
                authenticate(request, username=email, password=new_password)


            if changed_data:
                user_crud.update(db_obj=user, **changed_data)
                return redirect('my-profile')
        else:
            return render(request, template_name, {
                "form": form,
            })
    else:
        form = ProfileForm(instance=request.user)

    context = {
        'form': form,
    }
    return render(request, 'dashboard-my-profiles.html',context)



################### L O C A T I O N   H I S S E S I     U C H U N ####################################################################
def normalize_string(text):
    if not text:
        return ""
    
    text = str(text).lower().strip()
    text = text.replace('\\', ' ').replace('/', ' ')
    text = re.sub(r'\d+', '', text)
    
    garbage_words = [
        'qəsəbəsi', 'qesebesi', 'qəs.', 'qes.', 
        'massivi', 'massiv', 'sahəsi', 'sahesi', 'sahə', 'sahe',
        'bağları', 'baglari', 'bağlar', 'baglar', 
        'şəhəri', 'seheri', 'kəndi', 'kendi', 'siad', 'seide', 'dağ', 'dag',
        'rayonu', 'rayon', 'r.'
    ]
    for word in garbage_words:
        text = text.replace(word, '')
    
    mapping = {
        'ə': 'a', 'e': 'a', 'ö': 'o', 'ü': 'u', 'ı': 'i', 'ş': 's', 'ç': 'c', 'ğ': 'g'
    }
    for key, value in mapping.items():
        text = text.replace(key, value)
        
    return text.replace(" ", "").strip()

def get_similarity_ratio(str1, str2):
    """
    İki mətnin bir-birinə oxşarlıq dərəcəsini SequenceMatcher ilə təhlükəsiz ölçür.
    """
    if not str1 or not str2:
        return 0.0
    if str1 == str2:
        return 1.0
    
    # XƏTA BURADA İDİ: 'nullstream' silindi, yerinə standart None qoyuldu
    return SequenceMatcher(None, str1, str2).ratio()

def validate_map_location(request):
    try:
        target_district = request.GET.get('district', '').strip()
        target_village = request.GET.get('village', '').strip()

        city_obj = City.objects.filter(name__icontains="Bakı").first()
        if not city_obj:
            return JsonResponse({'error': 'Bakı şəhəri bazada tapılmadı.'}, status=404)

        response_data = {
            'city_id': city_obj.id,
            'area_id': None,
            'village_id': None,
            'areas': list(Area.objects.filter(city=city_obj).values('id', 'name').order_by('name')),
            'villages': []
        }

        norm_target_district = normalize_string(target_district)
        norm_target_village = normalize_string(target_village)

        matched_area = None
        matched_village = None

        # --- 1. DƏQİQ RAYON AXTARIŞI ---
        if norm_target_district:
            for area in Area.objects.filter(city=city_obj):
                if normalize_string(area.name) == norm_target_district:
                    matched_area = area
                    break

        # --- 2. QƏSƏBƏ AXTARIŞI ---
        if norm_target_village:
            # Addım A: Rayon bəllidirsə, rayon daxili tam bərabərlik
            if matched_area:
                for village in Village.objects.filter(area=matched_area):
                    if normalize_string(village.name) == norm_target_village:
                        matched_village = village
                        break
            
            # Addım B: Bütün Bakı üzrə DƏQİQ bərabərlik (==)
            if not matched_village:
                for village in Village.objects.filter(area__city=city_obj):
                    if normalize_string(village.name) == norm_target_village:
                        matched_village = village
                        matched_area = village.area
                        break

            # Addım C: Əgər heç bir TAM bərabərlik yoxdursa -> Safe Sequence Fuzzy Match
            if not matched_village:
                best_ratio = 0.0
                for village in Village.objects.filter(area__city=city_obj):
                    ratio = get_similarity_ratio(normalize_string(village.name), norm_target_village)
                    # Hərf ardıcıllığı ən azı %75 uyğun gəlməlidir
                    if ratio > best_ratio and ratio >= 0.75:
                        best_ratio = ratio
                        matched_area = village.area
                        if ratio >= 0.88:
                            matched_village = village

        # --- 3. REZERV RAYON OXŞARLIĞI ---
        if not matched_area and norm_target_district:
            best_ratio = 0.0
            for area in Area.objects.filter(city=city_obj):
                ratio = get_similarity_ratio(normalize_string(area.name), norm_target_district)
                if ratio > best_ratio and ratio >= 0.75:
                    best_ratio = ratio
                    matched_area = area

        if matched_area:
            response_data['area_id'] = matched_area.id
            response_data['villages'] = list(Village.objects.filter(area=matched_area).values('id', 'name').order_by('name'))
            
        if matched_village:
            response_data['village_id'] = matched_village.id

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)