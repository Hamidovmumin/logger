from django.contrib import admin
from .models import Category,City, Area, Village, Property, PropertyImage, Review, Reservation, Amenity, PropertyAmenity, Faqs
from django.utils.html import format_html


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 3  
    fields = ('image', 'is_allowed')

class PropertyAmenityInline(admin.TabularInline):
    model = PropertyAmenity
    extra = 1

@admin.register(Faqs)
class FaqsAdmin(admin.ModelAdmin):
    list_display = ['question']
    search_fields = ['question', 'answer']


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'city_image', 'created_at', 'updated_at')
    search_fields = ('name',)

    def city_image(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="80" height="50" style="object-fit:cover;">',
                obj.image.url
            )
        return "-"

    city_image.short_description = "Şəkil"

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'created_at')
    list_filter = ('city',)
    search_fields = ('name', 'city__name')

@admin.register(Village)
class VillageAdmin(admin.ModelAdmin):
    list_display = ('name', 'area', 'created_at')
    list_filter = ('area__city', 'area')
    search_fields = ('name', 'area__name')

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'status', 'price', 'city', 'is_sale', 'created_at')
    list_filter = ('status', 'category', 'is_sale', 'has_extract', 'city', 'is_renovated')
    search_fields = ('name', 'description', 'price')
    list_editable = ('status', 'price', 'is_sale') # Siyahıdan birbaşa dəyişmək üçün
    inlines = [PropertyImageInline, PropertyAmenityInline]
    prepopulated_fields= {"slug":("name",)}
    # Sahələri admin panelində qruplaşdırmaq üçün fieldsets
    fieldsets = (
        ("Ümumi Məlumat", {
            'fields': ('name','slug', 'category', 'status', 'description', 'image','phone')
        }),
        ("Məkan Məlumatları", {
            'fields': ('city', 'area', 'village', 'longitude', 'latitude')
        }),
        ("Qiymət və Vəziyyət", {
            'fields': ('price', 'is_sale', 'has_extract', 'is_renovated', 'has_mortgage','is_scraped')
        }),
        ("Texniki Göstəricilər", {
            'fields': ('square', 'floor_s', 'floor', 'room_count', )
        }),
        
    )

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('name', 'surname', 'prop', 'rating', 'is_allowed', 'created_at')
    list_filter = ('is_allowed', 'rating')
    list_editable = ('is_allowed',)  # Admin birbaşa siyahıdan rəyi təsdiqləyə bilsin
    search_fields = ('name', 'surname', 'description', 'prop__name')

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('name', 'surname', 'phone', 'created_at')
    search_fields = ('name', 'surname', 'phone', 'message')
    readonly_fields = ('created_at', 'updated_at') # Rezervasiya məlumatları dəyişdirilməsin deyə

@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)


admin.site.register(Category)