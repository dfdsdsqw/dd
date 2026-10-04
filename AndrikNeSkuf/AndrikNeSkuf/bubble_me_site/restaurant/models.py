from django.db import models
from django.utils.translation import get_language


def _t(uk, en):
    """Повертає англійський текст, якщо активна мова EN і він заповнений."""
    lang = get_language() or 'uk'
    if lang.startswith('en') and en:
        return en
    return uk


class Category(models.Model):
    name_uk = models.CharField("Назва (UA)", max_length=100)
    name_en = models.CharField("Name (EN)", max_length=100, blank=True)

    class Meta:
        verbose_name = "Категорія"
        verbose_name_plural = "Категорії"

    def __str__(self):
        return self.name_uk

    @property
    def name(self):
        return _t(self.name_uk, self.name_en)


class MenuItem(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='items',
        verbose_name="Категорія",
    )
    title_uk = models.CharField("Назва (UA)", max_length=150)
    title_en = models.CharField("Title (EN)", max_length=150, blank=True)
    description_uk = models.TextField("Опис (UA)", blank=True)
    description_en = models.TextField("Description (EN)", blank=True)
    price = models.DecimalField(
        "Ціна, грн (якщо немає версій)", max_digits=7, decimal_places=2,
        null=True, blank=True,
    )
    image = models.ImageField("Фото", upload_to='menu/', null=True, blank=True)

    class Meta:
        verbose_name = "Позиція меню"
        verbose_name_plural = "Позиції меню"

    def __str__(self):
        return self.title_uk

    @property
    def title(self):
        return _t(self.title_uk, self.title_en)

    @property
    def description(self):
        return _t(self.description_uk, self.description_en)


class MenuItemVariant(models.Model):
    item = models.ForeignKey(
        MenuItem, on_delete=models.CASCADE, related_name='variants',
        verbose_name="Позиція",
    )
    name_uk = models.CharField("Версія (UA)", max_length=50, blank=True,
                               help_text="Наприклад: Мала 300 мл")
    name_en = models.CharField("Version (EN)", max_length=50, blank=True,
                               help_text="For example: Small 300 ml")
    price = models.DecimalField("Ціна, грн", max_digits=7, decimal_places=2)

    class Meta:
        verbose_name = "Версія"
        verbose_name_plural = "Версії"
        ordering = ['price']

    def __str__(self):
        return f"{self.item.title_uk} / {self.name_uk or 'стандарт'}"

    @property
    def name(self):
        return _t(self.name_uk, self.name_en)


class News(models.Model):
    title_uk = models.CharField("Заголовок (UA)", max_length=200)
    title_en = models.CharField("Title (EN)", max_length=200, blank=True)
    content_uk = models.TextField("Текст (UA)")
    content_en = models.TextField("Content (EN)", blank=True)
    image = models.ImageField("Фото", upload_to='news/', null=True, blank=True)
    created_at = models.DateTimeField("Створено", auto_now_add=True)

    class Meta:
        verbose_name = "Новина"
        verbose_name_plural = "Новини"
        ordering = ['-created_at']

    def __str__(self):
        return self.title_uk

    @property
    def title(self):
        return _t(self.title_uk, self.title_en)

    @property
    def content(self):
        return _t(self.content_uk, self.content_en)


class ContactInfo(models.Model):
    address_uk = models.CharField("Адреса (UA)", max_length=255)
    address_en = models.CharField("Address (EN)", max_length=255, blank=True)
    phone = models.CharField("Телефон", max_length=30)
    instagram_link = models.URLField("Instagram", blank=True)
    google_maps_link = models.URLField("Google Maps", blank=True)

    class Meta:
        verbose_name = "Контакти"
        verbose_name_plural = "Контакти"

    def __str__(self):
        return self.address_uk

    @property
    def address(self):
        return _t(self.address_uk, self.address_en)


class AboutUs(models.Model):
    text_uk = models.TextField("Текст (UA)")
    text_en = models.TextField("Text (EN)", blank=True)

    class Meta:
        verbose_name = "Про нас"
        verbose_name_plural = "Про нас"

    def __str__(self):
        return "Про нас"

    @property
    def text(self):
        return _t(self.text_uk, self.text_en)