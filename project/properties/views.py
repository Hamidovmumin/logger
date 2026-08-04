from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.db.models import Avg,F,Q, Min, Max
from django.shortcuts import get_object_or_404, redirect, render
from django.core.cache import cache
from .models import Property, PropertyImage, Review,  PropertyAmenity,Category,City,Area,Village,Reservation,Category,Faqs
from .forms import ReservationForm,PropertyForm,PropertyImageForm, ReviewForm
from decimal import Decimal, InvalidOperation
from properties.models import Category, City
import math

def get_most_viewed_properties(limit=3):
    properties = Property.objects.filter(status=Property.Status.ACTIVE)

    property_views = []

    for prop in properties:
        views = cache.get(f"property-detail-{prop.id}", 0)
        property_views.append((prop, views))

    property_views.sort(key=lambda x: x[1], reverse=True)

    return [prop for prop, _ in property_views[:limit]]


def add_review(request, slug):
    prop = get_object_or_404(Property, slug=slug)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.prop = prop
            review.is_allowed = False  # admin/owner təsdiqinə qədər gizli
            review.save()
            messages.success(request, 'Rəyiniz üçün təşəkkürlər! Təsdiqdən sonra görünəcək.')
            return redirect('property_detail', slug=prop.slug)  # öz url adınla əvəz et
        messages.error(request, 'Formda xəta var, zəhmət olmasa yoxlayıb yenidən göndərin.')
    else:
        form = ReviewForm()

    return render(request, 'single-property-1.html', {
        'form': form,
        'property': prop,
    })

def get_city_prices():
    return {
        "sirvan": Property.objects.filter(city__name="Şirvan").aggregate(
            min_price=Min("price"), max_price=Max("price")
        ),
        "baki": Property.objects.filter(city__name="Bakı").aggregate(
            min_price=Min("price"), max_price=Max("price")
        ),
        "naxcivan": Property.objects.filter(city__name="Naxçıvan").aggregate(
            min_price=Min("price"), max_price=Max("price")
        ),
        "sumqayit": Property.objects.filter(city__name="Sumqayıt").aggregate(
            min_price=Min("price"), max_price=Max("price")
        ),
        "gence": Property.objects.filter(city__name="Gəncə").aggregate(
            min_price=Min("price"), max_price=Max("price")
        ),
    }

def get_city_images():
    sirvan = City.objects.filter(name="Şirvan").first()
    baki = City.objects.filter(name="Bakı").first()
    naxcivan = City.objects.filter(name="Naxçıvan").first()
    sumqayit = City.objects.filter(name="Sumqayıt").first()
    gence = City.objects.filter(name="Gəncə").first()

    
    return {
        "sirvan": sirvan.image.url if sirvan and sirvan.image else None,
        "baki": baki.image.url if baki and baki.image else None,
        "naxcivan": naxcivan.image.url if naxcivan and naxcivan.image else None,
        "sumqayit": sumqayit.image.url if sumqayit and sumqayit.image else None,
        "gence": gence.image.url if gence and gence.image else None,
    }


def get_favourite_ids(request):
    return request.session.get("favourites", [])


def save_favourite_ids(request, favourite_ids):
    request.session["favourites"] = favourite_ids
    request.session.modified = True



def index(request):
    sale_properties = Property.objects.filter(
        is_sale=True,
        status=Property.Status.ACTIVE
    )[:5]

    rent_properties = Property.objects.filter(
        is_sale=False,
        status=Property.Status.ACTIVE
    )[:5]

    most_viewed_properties = get_most_viewed_properties()

    total_properties = Property.objects.count()

    if request.method == "POST":
        form = ReservationForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Your message has been sent successfully.")
            return redirect("index")
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = ReservationForm()

    context = {
        "sale_properties": sale_properties,
        "rent_properties": rent_properties,
        "most_viewed_properties": most_viewed_properties,
        "total_properties": total_properties,
        "form": form,
        "city_prices": get_city_prices(),
        "city_images": get_city_images(),
        "categories": Category.objects.all().order_by("name"),
        "cities": City.objects.all().order_by("name"),
    }

    return render(request, "index.html", context)




def property_list(request):
    properties = Property.objects.select_related(
        'category',
        'city',
        'area',
        'village',
    ).filter(status=Property.Status.ACTIVE)

    def to_decimal(value):
        if value in [None, '']:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

    is_sale = request.GET.get('is_sale')
    if is_sale == 'true':
        properties = properties.filter(is_sale=True)
    elif is_sale == 'false':
        properties = properties.filter(is_sale=False)

    # Ümumi Axtarış sözü
    search = request.GET.get('search')
    if search:
        properties = properties.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(city__name__icontains=search) |
            Q(area__name__icontains=search) |
            Q(village__name__icontains=search) |
            Q(category__name__icontains=search)
        )

    # Kateqoriya
    category_id = request.GET.get('category')
    if category_id:
        properties = properties.filter(category_id=category_id)

    category_name = request.GET.get('category_name')
    if category_name:
        properties = properties.filter(category__name__icontains=category_name)

    # --- DÜZƏLİŞ: Otaq sayı (HTML-də name="min_rooms" olduğu üçün) ---
    min_rooms = request.GET.get('min_rooms')
    if min_rooms:
        try:
            # HTML-də dəyərlər "2", "3", "4", "5" olaraq gəlir və hamısı 2+ mənasını verir (gte)
            properties = properties.filter(room_count__gte=int(min_rooms))
        except (ValueError, TypeError):
            pass

    # Qiymət Aralığı
    min_price = to_decimal(request.GET.get('min_price'))
    max_price = to_decimal(request.GET.get('max_price'))
    if min_price is not None and max_price is not None and min_price > max_price:
        min_price, max_price = max_price, min_price

    if min_price is not None:
        properties = properties.filter(price__gte=min_price)
    if max_price is not None:
        properties = properties.filter(price__lte=max_price)

    # Sahə Aralığı
    min_square = to_decimal(request.GET.get('min_square'))
    max_square = to_decimal(request.GET.get('max_square'))
    if min_square is not None and max_square is not None and min_square > max_square:
        min_square, max_square = max_square, min_square

    if min_square is not None:
        properties = properties.filter(square__gte=min_square)
    if max_square is not None:
        properties = properties.filter(square__lte=max_square)

    # Təmir filtri
    is_renovated = request.GET.get('is_renovated')
    if is_renovated == 'true':
        properties = properties.filter(is_renovated=True)
    elif is_renovated == 'false':
        properties = properties.filter(is_renovated=False)

    # --- DÜZƏLİŞ: Kupça filtri (HTML-də <select> istifadə etdiyin üçün 'true'/'false' gəlir) ---
    has_extract = request.GET.get('has_extract')
    if has_extract == 'true':
        properties = properties.filter(has_extract=True)
    elif has_extract == 'false':
        properties = properties.filter(has_extract=False)

    # --- DÜZƏLİŞ: İpoteka filtri (HTML-də name="has_mortgage" olduğu üçün) ---
    has_mortgage = request.GET.get('has_mortgage')
    if has_mortgage == 'true':
        properties = properties.filter(has_mortgage=True)
    elif has_mortgage == 'false':
        # Əgər bazada boş (Null) qalanlar varsa, onları da bura daxil etmək üçün Q istifadə edə bilərsən
        properties = properties.filter(Q(has_mortgage=False) | Q(has_mortgage__isnull=True))

    # Lokasiya filtrləri
    city_ids = [c for c in request.GET.getlist('city') if c]
    if city_ids:
        properties = properties.filter(city_id__in=city_ids)

    city_name = request.GET.get('city_name')
    if city_name:
        properties = properties.filter(city__name__icontains=city_name)

    area_ids = [a for a in request.GET.getlist('area') if a]
    if area_ids:
        properties = properties.filter(area_id__in=area_ids)

    village_ids = [v for v in request.GET.getlist('village') if v]
    if village_ids:
        properties = properties.filter(village_id__in=village_ids)

    context = {
        'properties': properties,
        'categories': Category.objects.all().order_by('name'),
        'current_filters': request.GET,
        'cities': City.objects.all().order_by('name'),
        'areas': Area.objects.select_related('city').all().order_by('name'),
        'villages': Village.objects.select_related('area').all().order_by('name'),
        'selected_cities': city_ids,
        'selected_areas': area_ids,
        'selected_villages': village_ids,
    }

    return render(request, 'listing-full-width-grid-1.html', context)



def property_detail(request, slug):
    property_obj = get_object_or_404(Property, slug=slug)

    cache_key = f"property-detail-{property_obj.id}"
    try:
        detail_view = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=None)
        detail_view =1
    reviews = property_obj.reviews.filter(is_allowed=True).order_by('-created_at')

    total_reviews = reviews.count()
    average_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0

    rating_breakdown = []
    for star in range(5, 0, -1):
        count = reviews.filter(rating=star).count()
        percentage = round((count / total_reviews) * 100) if total_reviews else 0
        rating_breakdown.append({'star': star, 'count': count, 'percentage': percentage})

    session_key = request.session.session_key
    is_favourite = False

    if session_key:
        cache_key = f"favourites:{session_key}"
        favourites = cache.get(cache_key, [])
        is_favourite = property_obj.id in favourites

    images = property_obj.images.all()
    property_amenities = PropertyAmenity.objects.filter(prop=property_obj).select_related('amenity')

    similar_properties = Property.objects.filter(
        category=property_obj.category
    ).exclude(pk=property_obj.pk)[:6]

    context = {
        'property': property_obj,
        'images': images,
        'property_amenities': property_amenities,
        'similar_properties': similar_properties,
        'is_favourite': is_favourite,
        'reviews': reviews,
        'review_form': ReviewForm(),
        'total_reviews': total_reviews,
        'average_rating': average_rating,
        'average_rating_int': int(average_rating),
        'rating_breakdown': rating_breakdown,
        'detail_view': detail_view,
    }
    return render(request, 'single-property-1.html', context)

def about_us(request):
    return render(request, "about_us.html")


def contact_us(request):
    return render(request, "properties/contact_us.html")


def faqs(request):
    return render(request, "faqs.html")


def privacy_policy(request):
    return render(request, "properties/privacy_policy.html")

def add_favourite(request,pk,slug):
    session_key = request.session.session_key

    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    cache_key = f"favourites:{session_key}"

    favourites = cache.get(cache_key,[])
    if pk not in favourites:
        favourites.append(pk)

    cache.set(cache_key, favourites, timeout=60*60*24*7)  # 1 gün
    return redirect('property_detail',slug=slug)


def remove_favourite(request, pk):
    session_key = request.session.session_key

    if session_key:
        cache_key = f"favourites:{session_key}"
        favourites = cache.get(cache_key, [])

        if pk in favourites:
            favourites.remove(pk)
            # Şərhlə yazılan timeout 7 gün idi (60*60*24*7), kodu da şərhə uyğunlaşdırdım
            cache.set(cache_key, favourites, timeout=60*60*24*7) 

    # İstifadəçi haradan klikləyibsə, oraya geri qaytar (tapa bilməsə 'favourites' səhifəsinə göndər)
    return redirect(request.META.get('HTTP_REFERER', 'favourites'))

def favourites(request):
    session_key = request.session.session_key

    if not session_key:
        properties = Property.objects.none()
    else:
        cache_key = f"favourites:{session_key}"
        favourite_ids = cache.get(cache_key, [])

        properties = Property.objects.filter(id__in=favourite_ids)

    context = {
        "properties": properties,

    }
    return render(request, "favourites.html", context)

def contact_us(request):
    if request.method == "POST":
        form = ReservationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your contact request has been sent successfully!")
            return redirect('contact_us')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = ReservationForm()

    return render(request, 'contact-us-1.html', {'form': form})



def my_reservations(request):
    reservations = Reservation.objects.all()
    
    context = {
        "reservations": reservations,
    }
    
    return render(request, "my-reservations.html", context)

def property_edit(request, slug):
    property_obj = get_object_or_404(Property, slug=slug)
    
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES, instance=property_obj)
        image_form = PropertyImageForm(request.POST, request.FILES)
        
        if form.is_valid():
            updated_property = form.save()
            
            PropertyAmenity.objects.filter(prop=updated_property).delete()
            selected_amenities = form.cleaned_data.get('amenities')
            if selected_amenities:
                for amenity in selected_amenities:
                    PropertyAmenity.objects.create(prop=updated_property, amenity=amenity)
            
            files = request.FILES.getlist('images')  
            for f in files:
                PropertyImage.objects.create(
                    prop=updated_property,
                    image=f,
                    is_allowed=True  
                )
                
            messages.success(request, f'"{updated_property.name}" uğurla yeniləndi!')
            return redirect('dashboard') 
    else:
        form = PropertyForm(instance=property_obj)
        image_form = PropertyImageForm()
        
    current_images = property_obj.images.all()

    context = {
        'form': form,
        'image_form': image_form,
        'property': property_obj,
        'current_images': current_images,
    }
    return render(request, 'dashboard-property-edit.html', context)

def faqs(request):
    sale_properties = Property.objects.filter(
        is_sale=True,
        status=Property.Status.ACTIVE
    )[:5]

    rent_properties = Property.objects.filter(
        is_sale=False,
        status=Property.Status.ACTIVE
    )[:5]

    total_properties = Property.objects.count()

    faqs = list(Faqs.objects.all())
    mid = math.ceil(len(faqs) / 2)
    faqs_col1 = faqs[:mid]
    faqs_col2 = faqs[mid:]

    if request.method == "POST":
        form = ReservationForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Your message has been sent successfully.")
            return redirect("faqs")
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = ReservationForm()

    context = {
        "sale_properties": sale_properties,
        "rent_properties": rent_properties,
        "total_properties": total_properties,
        "form": form,
        "faqs_col1": faqs_col1,
        "faqs_col2": faqs_col2,
    }

    return render(request, "faqs.html", context)

def property_locations_api(request):
  
    properties = Property.objects.filter(
        status='active'
    ).exclude(latitude=0.0, longitude=0.0)

    locations_list = []
    for prop in properties:
        image_url = ""
        if prop.image:
            image_url = prop.image.url

     
        price = ""
        if prop.price:
            price = f"{int(prop.price):,} AZN".replace(",", " ")

        property_url = ""
        try:
            from django.urls import reverse
            property_url = reverse("property_detail", args=[prop.slug])
        except Exception:
            property_url = f"/properties/{prop.slug}/"

        address_parts = []
        if prop.city:
            address_parts.append(prop.city.name)
        if prop.area:
            address_parts.append(prop.area.name)
        if prop.village:
            address_parts.append(prop.village.name)

        address = ", ".join(address_parts) if address_parts else "Ünvan qeyd edilməyib"

        locations_list.append({
            "lat": float(prop.latitude),
            "lng": float(prop.longitude),
            'name': prop.name,
            "address": address,  
            "price": price,
            "image": image_url,
            "url": property_url
        })

    return JsonResponse({"locations": locations_list})