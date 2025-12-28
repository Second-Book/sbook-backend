import django_filters
from django.db.models import Q

from .models import Textbook


class TextbookFilter(django_filters.FilterSet):
    query = django_filters.CharFilter(method='in_title_or_desc',
                                      label='Search')
    author = django_filters.CharFilter(lookup_expr='icontains',
                                       label='Author')
    publisher = django_filters.CharFilter(lookup_expr='icontains',
                                          label='Publisher')
    school_class = django_filters.CharFilter(label='Grade')
    subject = django_filters.CharFilter(lookup_expr='icontains',
                                        label='Subject')
    min_price = django_filters.NumberFilter(field_name='price',
                                            lookup_expr='gte',
                                            label='Minimal price')
    max_price = django_filters.NumberFilter(field_name='price',
                                            lookup_expr='lte',
                                            label='Maximal price')
    condition = django_filters.ChoiceFilter(choices=Textbook.CONDITION_CHOICES)
    seller = django_filters.CharFilter(field_name='seller__username',
                                       lookup_expr='icontains',
                                       label='Seller')

    class Meta:
        model = Textbook
        fields = ['query', 'author', 'publisher', 'school_class',
                  'subject', 'price', 'condition', 'seller']

    def in_title_or_desc(self, queryset, name, value):
        return queryset.filter(
            Q(title__icontains=value) | Q(description__icontains=value)
        )
