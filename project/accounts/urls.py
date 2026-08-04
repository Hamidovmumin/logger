from django.urls import path
from django.contrib.auth.views import LoginView # 1. Add this import at the top
from . import views

from accounts.views import (login_view,email_verification_view,
                            reset_password_view,logout_view,my_profile_view)

urlpatterns = [
    # Dashboard
    path('dashboard/', views.DashboardIndexView.as_view(), name='dashboard'),
    # Add new
    path('add-new/', views.PropertyCreateView.as_view(), name='add_listing'),
    path('amenities/add/', views.amenity_add_ajax, name='amenity-add-ajax'),
    path('ajax/get-areas/', views.get_areas, name='get_areas'),
    path('ajax/get-villages/', views.get_villages, name='get_villages'),
    path('ajax/validate-map-location/', views.validate_map_location, name='validate_map_location'),


    # MyProperties
    path('my-properties/', views.dashboard_properties, name='my_properties'),
    path('my-properties/<int:pk>/edit/', views.PropertyUpdateView.as_view(), name='property_edit'),
    path('my-properties/<int:pk>/delete/', views.property_delete_view, name='property_delete'),
    
    # My Reservations
    path('reservations/', views.ReservationListView.as_view(), name='my_reservations'),
    path('reservations/<int:pk>/delete/', views.ReservationDeleteView.as_view(), name='delete_reservation'),

    #My Reviews
    path('reviews/', views.dashboard_reviews, name='dashboard-reviews'),
    path('reviews/<int:review_id>/toggle/', views.toggle_review, name='toggle-review'),
    path('reviews/<int:review_id>/delete/', views.delete_review, name='delete-review'),

    # My Profile
    path('dashboard/profile/', views.my_profile_view, name='my-profile'),

    path('auth/', login_view,name='login-admin'),
    path('auth/logout/', logout_view, name='logout-admin'),
    path('auth/email_verification/', email_verification_view,name='forgot-password'),
    path('auth/reset-password/', reset_password_view,name='reset-password'),
]