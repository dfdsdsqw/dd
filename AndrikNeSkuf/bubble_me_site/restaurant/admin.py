from django.contrib import admin
from django.utils.html import format_html

from .utils import notify_status_change
from .models import (
    Category, MenuItem, MenuItemVariant, News, ContactInfo, AboutUs,
    Order, OrderItem, VerifiedEmail,
)

admin.site.site_header = "BUBBLE ME · Адмін-панель"
admin.site.site_title = "BUBBLE ME"
admin.site.index_title = "Керування сайтом"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name_uk', 'name_en')


class MenuItemVariantInline(admin.TabularInline):
    model = MenuItemVariant
    extra = 2
    min_num = 0


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('title_uk', 'category', 'price')
    list_filter = ('category',)
    search_fields = ('title_uk', 'title_en')
    inlines = [MenuItemVariantInline]


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title_uk', 'created_at')


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ('address_uk', 'phone')


@admin.register(AboutUs)
class AboutUsAdmin(admin.ModelAdmin):
    list_display = ('__str__',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = ('title', 'variant', 'price', 'qty', 'line_total')
    readonly_fields = ('title', 'variant', 'price', 'qty', 'line_total')

    @admin.display(description="Сума, грн")
    def line_total(self, obj):
        return obj.price * obj.qty

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('number', 'created_at', 'name', 'phone', 'total_display', 'status_badge')
    list_display_links = ('number', 'name')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'phone', 'email')
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline]
    actions = ['mark_processing', 'mark_ready', 'mark_done', 'mark_cancelled']

    fields = ('number', 'status', 'eta_minutes', 'created_at', 'name', 'phone', 'email', 'comment', 'total')
    readonly_fields = ('number', 'created_at', 'name', 'phone', 'email', 'comment', 'total')

    COLORS = {
        'new': '#ff69b4', 'processing': '#f5a623', 'ready': '#2d9cdb',
        'done': '#2ea66a', 'cancelled': '#8f8389',
    }

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        new_count = Order.objects.filter(status='new').count()
        extra_context['title'] = f"Замовлення · нових: {new_count}" if new_count else "Замовлення"
        return super().changelist_view(request, extra_context)

    def save_model(self, request, obj, form, change):
        old_status = None
        if change and 'status' in form.changed_data:
            old_status = Order.objects.get(pk=obj.pk).status
        super().save_model(request, obj, form, change)
        if old_status is not None and old_status != obj.status:
            notify_status_change(obj)

    @admin.display(description="№", ordering='pk')
    def number(self, obj):
        return f"№{obj.pk}"

    @admin.display(description="Сума", ordering='total')
    def total_display(self, obj):
        return f"{obj.total} грн"

    @admin.display(description="Статус", ordering='status')
    def status_badge(self, obj):
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 12px;border-radius:999px;'
            'font-weight:700;font-size:12px">{}</span>',
            self.COLORS.get(obj.status, '#8f8389'), obj.get_status_display(),
        )

    def _bulk(self, request, queryset, status, label):
        changed = sum(1 for order in queryset if order.set_status(status))
        self.message_user(request, f"{label}: {changed}")

    @admin.action(description="Позначити як «Готується»")
    def mark_processing(self, request, queryset):
        self._bulk(request, queryset, 'processing', 'Готується')

    @admin.action(description="Позначити як «Готове, чекає на видачу» (клієнту піде лист)")
    def mark_ready(self, request, queryset):
        self._bulk(request, queryset, 'ready', 'Готове')

    @admin.action(description="Позначити як «Видане»")
    def mark_done(self, request, queryset):
        self._bulk(request, queryset, 'done', 'Видане')

    @admin.action(description="Позначити як «Скасоване» (клієнту піде лист)")
    def mark_cancelled(self, request, queryset):
        self._bulk(request, queryset, 'cancelled', 'Скасоване')

    def has_add_permission(self, request):
        return False


@admin.register(VerifiedEmail)
class VerifiedEmailAdmin(admin.ModelAdmin):
    list_display = ('email', 'verified_at')
    search_fields = ('email',)
    readonly_fields = ('email', 'verified_at')

    def has_add_permission(self, request):
        return False
