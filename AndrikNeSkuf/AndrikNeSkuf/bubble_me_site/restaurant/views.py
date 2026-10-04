from django.shortcuts import render, get_object_or_404
from django.utils import translation

from .models import Category, News, ContactInfo, AboutUs

LANGS = ('uk', 'en')


def get_lang(request):
    """Мова з ?lang=..., інакше із сесії, інакше українська."""
    lang = request.GET.get('lang')
    if lang in LANGS:
        request.session['lang'] = lang
    return request.session.get('lang', 'uk')


def home(request):
    lang = get_lang(request)
    with translation.override(lang):
        context = {
            'categories': Category.objects.prefetch_related('items__variants'),
            'news_list': News.objects.all()[:3],
            'contact': ContactInfo.objects.first(),
            'about': AboutUs.objects.first(),
            'lang': lang,
        }
        return render(request, 'restaurant/home.html', context)


def news_detail(request, pk):
    lang = get_lang(request)
    with translation.override(lang):
        context = {
            'news': get_object_or_404(News, pk=pk),
            'contact': ContactInfo.objects.first(),
            'lang': lang,
        }
        return render(request, 'restaurant/news_detail.html', context)