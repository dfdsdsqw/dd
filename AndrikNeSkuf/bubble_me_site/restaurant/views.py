import json
import re
from datetime import timedelta
from decimal import Decimal

from django.core import signing
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone, translation
from django.views.decorators.http import require_POST

from .models import (
    Category, News, ContactInfo, AboutUs,
    MenuItem, MenuItemVariant, Order, OrderItem, VerifiedEmail,
)
from .utils import (
    SALT, CONFIRM_MAX_AGE, normalize_phone,
    send_order_confirmation, notify_admin_new_order,
)

LANGS = ('uk', 'en')

# Не більше 5 замовлень з однієї адреси за 10 хвилин
RATE_LIMIT = 5
RATE_WINDOW = 600

MESSAGES = {
    'uk': {
        'name': "Введіть ім'я",
        'phone': 'Номер не знайдено. Перевірте цифри',
        'email': 'Введіть коректний email',
        'items': 'Кошик порожній або містить недоступні позиції',
        'spam': 'Не вдалося надіслати замовлення. Спробуйте ще раз',
        'rate': 'Забагато замовлень. Спробуйте трохи пізніше',
    },
    'en': {
        'name': 'Please enter your name',
        'phone': 'Number not found. Please check the digits',
        'email': 'Enter a valid email',
        'items': 'Your cart is empty or contains unavailable items',
        'spam': 'Could not send the order. Please try again',
        'rate': 'Too many orders. Please try again later',
    },
}


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


def _parse_lines(raw_items):
    """Перевіряє кошик і бере ціни з бази даних, а не з браузера."""
    if not isinstance(raw_items, list) or not 0 < len(raw_items) <= 50:
        return None
    lines = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            return None
        try:
            item_id = int(raw.get('item'))
            variant_id = int(raw.get('variant') or 0)
            qty = int(raw.get('qty'))
        except (TypeError, ValueError):
            return None
        if not 1 <= qty <= 50:
            return None

        item = MenuItem.objects.filter(pk=item_id).first()
        if item is None:
            return None

        if variant_id:
            variant = MenuItemVariant.objects.filter(pk=variant_id, item=item).first()
            if variant is None:
                return None
            lines.append((item.title_uk, variant.name_uk, variant.price, qty))
        else:
            if item.price is None:
                return None
            lines.append((item.title_uk, '', item.price, qty))
    return lines


@require_POST
def create_order(request):
    lang = get_lang(request)
    msg = MESSAGES[lang]

    try:
        data = json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'errors': {'items': msg['spam']}}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({'ok': False, 'errors': {'items': msg['spam']}}, status=400)

    # Приманка для ботів: людина це приховане поле не бачить і не заповнює
    if data.get('hp'):
        return JsonResponse({'ok': False, 'errors': {'items': msg['spam']}}, status=400)

    ip = request.META.get('REMOTE_ADDR', '')
    rate_key = f'order-rate:{ip}'
    if cache.get(rate_key, 0) >= RATE_LIMIT:
        return JsonResponse({'ok': False, 'errors': {'items': msg['rate']}}, status=429)

    name = str(data.get('name', '')).strip()[:100]
    email = str(data.get('email', '')).strip().lower()[:254]
    comment = str(data.get('comment', '')).strip()[:1000]
    phone = normalize_phone(data.get('phone', ''))

    errors = {}
    if not name:
        errors['name'] = msg['name']
    if phone is None:
        errors['phone'] = msg['phone']
    try:
        validate_email(email)
    except ValidationError:
        errors['email'] = msg['email']

    lines = _parse_lines(data.get('items'))
    if lines is None:
        errors['items'] = msg['items']

    if errors:
        return JsonResponse({'ok': False, 'errors': errors}, status=400)

    with transaction.atomic():
        order = Order.objects.create(
            name=name, email=email, phone=phone, comment=comment, lang=lang,
            total=sum((price * qty for _, _, price, qty in lines), Decimal('0')),
        )
        OrderItem.objects.bulk_create([
            OrderItem(order=order, title=title, variant=variant, price=price, qty=qty)
            for title, variant, price, qty in lines
        ])

    cache.set(rate_key, cache.get(rate_key, 0) + 1, RATE_WINDOW)

    # Листи (помилка пошти не скасовує замовлення)
    send_order_confirmation(order, request)
    notify_admin_new_order(order)

    return JsonResponse({
        'ok': True,
        'number': order.pk,
        'token': order.token,
        'verified': VerifiedEmail.objects.filter(email=order.email).exists(),
    })


@require_POST
def order_status(request):
    """Статуси замовлень за секретними токенами, які браузер зберіг у клієнта."""
    try:
        data = json.loads(request.body)
        tokens = data.get('tokens', [])
    except (ValueError, TypeError, AttributeError):
        return JsonResponse({'orders': []}, status=400)
    if not isinstance(tokens, list):
        return JsonResponse({'orders': []}, status=400)

    tokens = [t for t in tokens if isinstance(t, str) and 10 <= len(t) <= 40][:10]
    if not tokens:
        return JsonResponse({'orders': []})

    since = timezone.now() - timedelta(days=7)
    orders = list(
        Order.objects.filter(token__in=tokens, created_at__gte=since).prefetch_related('items')
    )
    verified = set(
        VerifiedEmail.objects.filter(email__in={o.email for o in orders})
        .values_list('email', flat=True)
    )
    now = timezone.now()
    result = []
    for o in orders:
        result.append({
            'token': o.token,
            'number': o.pk,
            'status': o.status,
            'eta': o.eta_minutes,
            'total': str(o.total),
            'age_minutes': int((now - o.updated_at).total_seconds() // 60),
            'verified': o.email in verified,
            'items': [{'title': i.title, 'variant': i.variant, 'qty': i.qty} for i in o.items.all()],
        })
    return JsonResponse({'orders': result})


def confirm_email(request, token):
    lang = get_lang(request)
    ok = False
    try:
        data = signing.loads(token, salt=SALT, max_age=CONFIRM_MAX_AGE)
        VerifiedEmail.objects.get_or_create(email=str(data['e']).lower())
        ok = True
    except (signing.BadSignature, KeyError, TypeError):
        pass
    with translation.override(lang):
        return render(request, 'restaurant/confirm.html', {
            'ok': ok, 'lang': lang, 'contact': ContactInfo.objects.first(),
        })
