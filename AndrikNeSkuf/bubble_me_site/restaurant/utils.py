import logging
import re
from decimal import Decimal

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMultiAlternatives, send_mail
from django.urls import reverse
from django.utils.html import escape

from .models import VerifiedEmail

logger = logging.getLogger(__name__)

# Коди українських мобільних операторів (після +380)
MOBILE_CODES = {
    '39', '50', '63', '66', '67', '68', '73',
    '91', '92', '93', '94', '95', '96', '97', '98', '99',
}
SALT = 'bubble-email-confirm'
CONFIRM_MAX_AGE = 7 * 24 * 3600


def normalize_phone(raw):
    """Повертає '+380XXXXXXXXX' або None, якщо такого номера не може існувати."""
    digits = re.sub(r'\D', '', str(raw))
    if digits.startswith('380'):
        digits = digits[3:]
    digits = digits.lstrip('0')
    if len(digits) != 9 or digits[:2] not in MOBILE_CODES:
        return None
    return '+380' + digits


def fmt_money(value):
    text = f"{Decimal(value):.2f}"
    return text[:-3] if text.endswith('.00') else text


TEXTS = {
    'uk': {
        'currency': 'грн',
        'hello': 'Привіт, {name}!',
        'new_subject': 'BUBBLE ME: замовлення №{n} прийнято',
        'new_lead': 'Ваше замовлення №{n} прийнято. Дякуємо, що обрали BUBBLE ME!',
        'items_title': 'Що в замовленні:',
        'total': 'Разом',
        'new_tail': 'Коли замовлення буде готове, ми повідомимо вас листом. '
                    'Статус також видно на нашому сайті.',
        'confirm_lead': 'Підтвердіть пошту, і наступного разу ми самі заповнимо ваші дані в замовленні:',
        'confirm_btn': 'Підтвердити пошту',
        'ready_subject': 'BUBBLE ME: замовлення №{n} готове!',
        'ready_lead': 'Ваше замовлення №{n} готове й чекає на вас. Смачного!',
        'cancelled_subject': 'BUBBLE ME: замовлення №{n} скасовано',
        'cancelled_lead': 'Ваше замовлення №{n} скасовано. Якщо це сталося помилково, '
                          'будь ласка, зв’яжіться з нами.',
        'bye': 'З теплом, команда BUBBLE ME',
    },
    'en': {
        'currency': 'UAH',
        'hello': 'Hi, {name}!',
        'new_subject': 'BUBBLE ME: order No. {n} received',
        'new_lead': 'Your order No. {n} has been received. Thank you for choosing BUBBLE ME!',
        'items_title': 'Your order:',
        'total': 'Total',
        'new_tail': 'We will email you as soon as your order is ready. '
                    'You can also follow its status on our website.',
        'confirm_lead': 'Confirm your email and next time we will fill in your details for you:',
        'confirm_btn': 'Confirm email',
        'ready_subject': 'BUBBLE ME: order No. {n} is ready!',
        'ready_lead': 'Your order No. {n} is ready and waiting for you. Enjoy!',
        'cancelled_subject': 'BUBBLE ME: order No. {n} cancelled',
        'cancelled_lead': 'Your order No. {n} has been cancelled. If this is a mistake, please contact us.',
        'bye': 'Warm regards, the BUBBLE ME team',
    },
}


def _texts(order):
    return TEXTS.get(order.lang, TEXTS['uk'])


def _item_lines(order, T):
    lines = []
    for it in order.items.all():
        name = f"{it.title} ({it.variant})" if it.variant else it.title
        lines.append((name, it.qty, fmt_money(it.price * it.qty)))
    return lines


def _build(order, T, lead, with_items=False, tail='', confirm_url=''):
    text = [T['hello'].format(name=order.name), '', lead, '']
    html = [
        f'<p style="margin:0 0 12px;font-size:16px">{escape(T["hello"].format(name=order.name))}</p>',
        f'<p style="margin:0 0 16px;font-size:16px"><b>{escape(lead)}</b></p>',
    ]
    if with_items:
        text.append(T['items_title'])
        rows = ''
        for name, qty, line_sum in _item_lines(order, T):
            text.append(f"  • {name} × {qty} — {line_sum} {T['currency']}")
            rows += (f'<tr><td style="padding:4px 0">{escape(name)} × {qty}</td>'
                     f'<td style="padding:4px 0;text-align:right">{line_sum} {T["currency"]}</td></tr>')
        total = fmt_money(order.total)
        text += [f"{T['total']}: {total} {T['currency']}", '']
        html.append(
            f'<p style="margin:0 0 6px;font-weight:700">{escape(T["items_title"])}</p>'
            f'<table style="width:100%;border-collapse:collapse;font-size:15px">{rows}'
            f'<tr><td style="padding:8px 0;border-top:2px solid #ffb6c1"><b>{escape(T["total"])}</b></td>'
            f'<td style="padding:8px 0;border-top:2px solid #ffb6c1;text-align:right"><b>{total} {T["currency"]}</b></td></tr>'
            f'</table>')
    if tail:
        text += [tail, '']
        html.append(f'<p style="margin:16px 0 0;color:#6b5f65">{escape(tail)}</p>')
    if confirm_url:
        text += [T['confirm_lead'], confirm_url, '']
        html.append(
            f'<p style="margin:20px 0 10px">{escape(T["confirm_lead"])}</p>'
            f'<a href="{escape(confirm_url)}" style="display:inline-block;background:#2d2529;color:#fff;'
            f'text-decoration:none;padding:12px 26px;border-radius:999px;font-weight:700">'
            f'{escape(T["confirm_btn"])}</a>')
    text.append(T['bye'])
    html.append(f'<p style="margin:24px 0 0;color:#8f8389">{escape(T["bye"])}</p>')

    html_doc = (
        '<div style="background:#fff5ee;padding:24px;font-family:Arial,Helvetica,sans-serif;color:#2d2529">'
        '<div style="max-width:520px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden">'
        '<div style="background:#ffb6c1;padding:18px 24px;font-size:22px;font-weight:700">BUBBLE ME</div>'
        '<div style="padding:24px">' + ''.join(html) + '</div></div></div>'
    )
    return '\n'.join(text), html_doc


def _send(subject, text, html, to):
    msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [to])
    msg.attach_alternative(html, 'text/html')
    msg.send()


def send_order_confirmation(order, request=None):
    """Лист клієнту: замовлення прийнято. Помилка пошти не ламає замовлення."""
    try:
        T = _texts(order)
        confirm_url = ''
        if request is not None and not VerifiedEmail.objects.filter(email=order.email).exists():
            token = signing.dumps({'e': order.email}, salt=SALT)
            confirm_url = request.build_absolute_uri(reverse('confirm_email', args=[token]))
        text, html = _build(order, T, T['new_lead'].format(n=order.pk),
                            with_items=True, tail=T['new_tail'], confirm_url=confirm_url)
        _send(T['new_subject'].format(n=order.pk), text, html, order.email)
    except Exception:
        logger.exception('Не вдалося надіслати лист клієнту (замовлення %s)', order.pk)


def notify_status_change(order):
    """Лист клієнту, коли замовлення готове або скасоване."""
    if order.status not in ('ready', 'cancelled'):
        return
    try:
        T = _texts(order)
        key = order.status
        text, html = _build(order, T, T[f'{key}_lead'].format(n=order.pk))
        _send(T[f'{key}_subject'].format(n=order.pk), text, html, order.email)
    except Exception:
        logger.exception('Не вдалося надіслати лист про статус (замовлення %s)', order.pk)


def notify_admin_new_order(order):
    recipients = list(getattr(settings, 'ORDER_NOTIFY_EMAIL', []) or [])
    if not recipients:
        return
    try:
        lines = [f"Нове замовлення №{order.pk}",
                 f"Клієнт: {order.name}, {order.phone}, {order.email}"]
        for it in order.items.all():
            name = f"{it.title} ({it.variant})" if it.variant else it.title
            lines.append(f"  • {name} × {it.qty}")
        lines.append(f"Разом: {fmt_money(order.total)} грн")
        if order.comment:
            lines.append(f"Коментар: {order.comment}")
        send_mail(f"BUBBLE ME: нове замовлення №{order.pk}", '\n'.join(lines),
                  settings.DEFAULT_FROM_EMAIL, recipients)
    except Exception:
        logger.exception('Не вдалося надіслати лист адміну (замовлення %s)', order.pk)
