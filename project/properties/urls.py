from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("properties/", views.property_list, name="property_list"),
    path("properties/<slug:slug>/", views.property_detail, name="property_detail"),
    path("about/", views.about_us, name="about_us"),
    path("contact/", views.contact_us, name="contact_us"),
    path("faqs/", views.faqs, name="faqs"),
    path("privacy-policy/", views.privacy_policy, name="privacy_policy"),
    path("favourites/", views.favourites, name="favourites"),
    path('my-reservations/', views.my_reservations, name='my_reservations'),
    path('property-list/', views.property_list, name='property_list'),
    path("properties/<int:pk>/<slug:slug>/favourite/", views.add_favourite, name="add-favourite"),
    path("properties/<int:pk>/remove-favourite/",views.remove_favourite,name="remove-favourite"),
    path("api/property-locations/", views.property_locations_api, name="property_locations_api"),
    path('property/<slug:slug>/review/', views.add_review, name='add-review'),
]
