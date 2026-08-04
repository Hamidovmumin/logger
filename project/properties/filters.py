import django_filters
from .models import Property, Review

class PropertyFilter(django_filters.FilterSet):

    price_min = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='price', lookup_expr='lte')

    year_min = django_filters.NumberFilter(field_name='year_built', lookup_expr='gte')
    year_max = django_filters.NumberFilter(field_name='year_built', lookup_expr='lte')

    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = Property
        fields = [
            'city',
            'area',
            'village',
            'category',
            'prop_type',
            'status',
            'is_sale',
            'room_count',
            
            'floor',
            'has_heating',
            'garage',
            'is_renovated',
            'has_extract',
            'has_mortgage',
        ]


class ReviewFilter(django_filters.FilterSet):

    class Meta:
        model = Review
        fields = [
            'prop',
            'is_allowed',
            'rating',
        ]