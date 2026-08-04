from decimal import Decimal

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify

from config.settings import AUTH_USER_MODEL

class TimeStamp(models.Model):
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        abstract=True




class Category(TimeStamp):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Categories'




class City(TimeStamp):
    name=models.CharField(max_length=100, unique=True)
    image=models.ImageField(upload_to='cities/',max_length=255, null=True, blank=True)
    def __str__(self):
        return self.name
    class Meta:
        verbose_name_plural='Cities'

        

class Area(TimeStamp):
    city=models.ForeignKey(City, on_delete=models.CASCADE, related_name='areas')
    name=models.CharField(max_length=100)
    def __str__(self):
        return f'{self.name}, {self.city.name}'


class Village(TimeStamp):
    area=models.ForeignKey(Area, on_delete=models.CASCADE, related_name='villages')
    name=models.CharField(max_length=100)
    def __str__(self):
        return f'{self.name}, {self.area.name}'
    


class Faqs(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()

    def __str__(self):
        return self.question
    
    class Meta:
        verbose_name_plural='Faqs'
    

class Property(TimeStamp):    
    slug = models.SlugField(max_length=250, unique=True, null=True, blank=True)
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Aktiv'
        INACTIVE = 'inactive', 'Deaktiv'
        
    image = models.ImageField(upload_to='properties/',max_length=255) 
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, related_name='properties')
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True, related_name='properties')
    village = models.ForeignKey(Village, on_delete=models.SET_NULL, null=True, blank=True, related_name='properties')
    
    # 2. Changed from CharField to ForeignKey
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='properties'
    )
    
    latitude = models.DecimalField(
    max_digits=9,
    decimal_places=6,
    default=Decimal("0.000000")
    )

    longitude = models.DecimalField(
    max_digits=9,
    decimal_places=6,
    default=Decimal("0.000000")
    )

    name = models.CharField(max_length=200)
    status=models.CharField(max_length=10,choices=Status.choices, default=Status.ACTIVE)
    is_sale=models.BooleanField(default=True) #True=satis ucun, False=kirayə
    price=models.DecimalField(max_digits=12, decimal_places=2)
    square=models.FloatField() #umumi sahe
    floor_s=models.IntegerField(null=True, blank=True) #mertebenin sayi
    room_count=models.IntegerField(null=True, blank=True)
    floor=models.IntegerField(null=True, blank=True)
    is_renovated=models.BooleanField(default=False) #temirli
    has_mortgage=models.BooleanField(default=False) #ipotekali
    description=models.TextField(null=True,blank=True)
    has_extract=models.BooleanField(default=False)  #cixaris kagizi /kupca
    phone = models.CharField(max_length=20, null=True, blank=True)
    is_scraped=models.BooleanField(default=False)

    @property
    def cover_image(self):
        return self.images.filter(is_cover=True).first()

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            
            base_slug = slugify(self.name)
            if not base_slug:
                base_slug = "property"  
                
            slug = base_slug
            counter = 1
            
            
            while Property.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
                
            self.slug = slug
            
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'Properties'
        ordering = ['-created_at']







class PropertyImage(TimeStamp):
    image = models.ImageField(upload_to='properties/', max_length=255)
    is_allowed = models.BooleanField(default=False)
    prop = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    is_cover = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not PropertyImage.objects.filter(prop=self.prop, is_cover=True).exists():
            self.is_cover = True
        super().save(*args, **kwargs)



class Review(TimeStamp):
    name=models.CharField(max_length=100)
    surname=models.CharField(max_length=100,null=True,blank=True)
    description=models.TextField(null=True, blank=True)
    rating=models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    is_allowed=models.BooleanField(default=False)  #admin tesdiqi ucun
    prop = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='reviews')
    def __str__(self):
        return f'{self.name}-- ({self.rating} stars)'
    class Meta:
        ordering=['-created_at']

class Reservation(TimeStamp):
    name=models.CharField(max_length=20)
    surname=models.CharField(max_length=20,null=True,blank=True)
    phone=models.CharField(max_length=16)
    message=models.TextField(max_length=500)
    email = models.EmailField(blank=True, null=True)
    def __str__(self):
        return f'{self.name}--{self.phone}'
    class Meta:
        ordering=['-created_at']#yeniden kohneye sira 




class Amenity(TimeStamp):
    name=models.CharField(max_length=100)
    def __str__(self):
        return self.name



class PropertyAmenity(TimeStamp):
    prop=models.ForeignKey(Property,on_delete=models.SET_NULL, null=True)
    amenity=models.ForeignKey(Amenity,on_delete=models.SET_NULL, null=True)