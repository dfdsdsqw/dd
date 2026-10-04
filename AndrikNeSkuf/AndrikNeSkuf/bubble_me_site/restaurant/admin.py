from django.contrib import admin
from .models import Category, MenuItem, MenuItemVariant, News, ContactInfo, AboutUs


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