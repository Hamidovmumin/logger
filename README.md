# django-view-logger

Django layihələri üçün sıfırdan yazılmış, `logging` modulundan asılı
olmayan, tam **reusable** terminal logger modulu.

- Python-un standart `logging` modulu **istifadə edilmir**.
- Django-nun `LOGGING` konfiqurasiyasından asılı deyil.
- Heç bir konkret app, model və ya User modelinə bağlı deyil.
- Başqa Django layihəsinə sadəcə qovluğu köçürməklə (copy-paste) işə düşür.

---

## 1. Məqsəd

Modul iki class-dan ibarətdir:

| Class | Vəzifəsi |
|---|---|
| `BaseLogger` | Terminala yazma, formatlaşdırma, səviyyə idarəetməsi, həssas məlumatların gizlədilməsi |
| `ViewLogger` | `BaseLogger`-dən miras alır, Django `request` obyektindən context çıxarır |

Bütün loglar eyni formatda çap olunur:

```
[TARİX] [SƏVİYYƏ] [LOGGER ADI] MESAJ | ƏLAVƏ MƏLUMATLAR
```

Nümunə:

```
[2026-07-30 15:45:12] [INFO] [view.owner_list] Request başladı | request_id=ab12cd34 | method=GET | path=/owners/ | user_id=5
```

`DEBUG`, `INFO`, `SUCCESS` → `stdout`
`WARNING`, `ERROR`, `CRITICAL` → `stderr`

---

## 2. Quraşdırma

Xarici paket asılılığı yoxdur. `django_view_logger` qovluğunu birbaşa
layihənin kök qovluğuna (və ya hər hansı Python path-inə düşən yerə)
köçürün:

```
your_project/
├── manage.py
├── django_view_logger/     <- bu qovluğu köçürün
│   ├── __init__.py
│   ├── base.py
│   └── view_logger.py
└── owners/
    └── views.py
```

Sonra istənilən yerdən belə import edin:

```python
from django_view_logger import BaseLogger, ViewLogger
```

---

## 3. `BaseLogger` istifadəsi

`BaseLogger` heç bir Django-ya bağlı deyil, Django xaricində (Celery
task-ları, management command-lar, adi script-lər) də istifadə edilə
bilər.

```python
from django_view_logger import BaseLogger

logger = BaseLogger(name="scraper.emlaksat")

logger.debug("Səhifə açıldı", url="https://emlaksat.az/page/1")
logger.info("Elan tapıldı", listing_id=123)
logger.success("Scraping tamamlandı", total=250)
logger.warning("Redis cache boşdur")
logger.error("Şəkil yüklənmədi", image_url="...")
logger.critical("Verilənlər bazasına qoşulma alınmadı")
```

### `bind()` ilə context əlavə etmək

`bind()` mövcud logger-i dəyişmir, üzərinə yeni context əlavə olunmuş
**yeni** logger instance-ı qaytarır:

```python
task_logger = logger.bind(task_id=42, celery_task="scrape_listings")
task_logger.info("Tapşırıq başladı")
# ... | task_id=42 | celery_task=scrape_listings
```

---

## 4. `ViewLogger` istifadəsi

### Function-based view nümunəsi

```python
from django.http import JsonResponse
from django_view_logger import ViewLogger


def owner_list(request):
    logger = ViewLogger.from_request(request, view_name="owner_list")
    logger.request_started()

    try:
        owners = list_owners()
        logger.message("Sahibkar məlumatları tapıldı", owner_count=len(owners))
    except Exception as exc:
        logger.request_error("View işləyərkən xəta baş verdi", exception=exc)
        return JsonResponse({"detail": "Server xətası"}, status=500)

    logger.request_finished(status_code=200)
    return JsonResponse({"owners": owners})
```

### Class-based view nümunəsi

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from django_view_logger import ViewLogger


class OwnerDetailView(APIView):
    def get(self, request, pk):
        logger = ViewLogger.from_request(request, view_name="owner_detail")
        logger.request_started()

        owner = Owner.objects.filter(pk=pk).first()
        if owner is None:
            logger.not_found("Sahibkar tapılmadı", owner_id=pk)
            return Response({"detail": "Tapılmadı"}, status=404)

        if not request.user.has_perm("owners.view_owner"):
            logger.permission_denied(
                "İstifadəçinin bu əməliyyata icazəsi yoxdur",
                owner_id=pk,
            )
            return Response({"detail": "İcazə yoxdur"}, status=403)

        logger.request_finished(status_code=200)
        return Response({"id": owner.pk, "name": owner.name})
```

`ViewLogger.from_request()` `request` obyektindən avtomatik olaraq
aşağıdakı context-i çıxarır və hər log mesajına əlavə edir:

- `view_name`
- `method`
- `path`
- `user_id`, `username` (custom User modeli ilə də işləyir, `getattr` ilə generic alınır)
- `ip_address` (`X-Forwarded-For` və ya `REMOTE_ADDR`)
- `query_params`
- `request_id` (`X-Request-Id` header-i varsa oradan, yoxdursa avtomatik generasiya olunur)

---

## 5. Log səviyyələri

| Səviyyə | Dəyər | İstifadə yeri |
|---|---|---|
| `DEBUG` | 10 | Development zamanı ətraflı izləmə |
| `INFO` | 20 | Adi məlumatlandırıcı mesajlar |
| `SUCCESS` | 25 | Uğurla tamamlanan əməliyyatlar |
| `WARNING` | 30 | Validation, not-found, permission kimi gözlənilən problemlər |
| `ERROR` | 40 | Gözlənilməyən xətalar |
| `CRITICAL` | 50 | Sistemin işləməsinə mane olan kritik xətalar |

`min_level` parametri ilə göstəriləcək minimum səviyyəni məhdudlaşdıra
bilərsiniz:

```python
logger = BaseLogger(name="worker", min_level="WARNING")
logger.debug("Bu görünməyəcək")
logger.warning("Bu görünəcək")
```

---

## 6. Exception nümunəsi

```python
try:
    result = risky_operation()
except Exception as exc:
    logger.request_error("View işləyərkən xəta baş verdi", exception=exc)
```

Terminal çıxışı:

```
[2026-07-30 15:46:02] [ERROR] [view.owner_list] View işləyərkən xəta baş verdi | ... | exception_type=ValueError | exception_message=...
Traceback (most recent call last):
  ...
ValueError: ...
```

`BaseLogger.exception()` metodu da eyni şəkildə birbaşa istifadə edilə bilər:

```python
try:
    1 / 0
except Exception as exc:
    logger.exception("Gözlənilməz xəta", exc=exc)
```

---

## 7. Həssas məlumatların gizlədilməsi

Aşağıdakı açar adları (böyük/kiçik hərfə həssas olmadan) avtomatik
`***` ilə əvəz olunur, nested dictionary-lər daxilində də:

```
password, password1, password2, token, access_token, refresh_token,
authorization, cookie, sessionid, csrfmiddlewaretoken, otp, pin,
secret, api_key
```

```python
logger.info(
    "Login məlumatları",
    username="huseynov01",
    password="123456",
    token="secret-token",
)
```

Terminal:

```
... Login məlumatları | username=huseynov01 | password=*** | token=***
```

Nested dict nümunəsi:

```python
logger.info(
    "Request məlumatları",
    data={
        "username": "huseynov01",
        "credentials": {"password": "123456", "token": "abc"},
    },
)
```

Terminal:

```
... Request məlumatları | data={'username': 'huseynov01', 'credentials': {'password': '***', 'token': '***'}}
```

---

## 8. Loglari bazaya yazmaq (`LogEntry` modeli)

Paket eyni zamanda `LogEntry` adlı Django modeli ilə gəlir. Bu, tamamilə
**istəyə bağlıdır** — istəməsən heç toxunmursan, modul əvvəlki kimi
sadəcə terminala yazır.

### Qurulum

`settings.py`-da `INSTALLED_APPS`-a əlavə et:

```python
INSTALLED_APPS = [
    ...
    "django_view_logger",
]
```

Sonra adi migration əmrini işlət:

```bash
python manage.py migrate
```

Bu, `django_view_logger_logentry` cədvəlini avtomatik yaradacaq
(migration artıq paketin daxilində hazırdır, ayrıca `makemigrations`
işlətməyə ehtiyac yoxdur).

> **Qeyd:** `context` sahəsi `JSONField` istifadə edir, bu da Django 3.1+
> tələb edir.

### İstifadəsi

Hər hansı logger yaradanda sadəcə `db_log=True` ötür:

```python
from django_view_logger import BaseLogger

logger = BaseLogger(name="scraper.emlaksat", db_log=True)
logger.info("Scraping başladı")   # həm terminala, həm bazaya yazılır
```

```python
from django_view_logger import ViewLogger

logger = ViewLogger.from_request(request, view_name="owner_list", db_log=True)
logger.request_started()          # həm terminala, həm bazaya yazılır
```

`bind()` ilə yaradılan logger-lər də `db_log` parametrini avtomatik
miras alır:

```python
task_logger = logger.bind(task_id=42)   # db_log dəyəri qorunur
```

### Nə saxlanılır

Hər qeyd (`LogEntry`) bunlardan ibarətdir:

| Sahə | Təsvir |
|---|---|
| `level` | `DEBUG` / `INFO` / `SUCCESS` / `WARNING` / `ERROR` / `CRITICAL` |
| `logger_name` | logger-in adı (məs. `view.owner_list`) |
| `message` | log mesajının mətni |
| `context` | bind edilmiş context + o çağırışın əlavə məlumatları (JSON, həssas sahələr maskalanmış) |
| `created_at` | avtomatik tarix-vaxt |

`min_level` filtri burda da tətbiq olunur — göstərilməyən (filtrlənən)
loglar bazaya da yazılmır.

### Admin panel (istəyə bağlı)

`admin.py` faylı hazır gəlir. Django admin işlədirsənsə, loglar
avtomatik admin panelində görünəcək (`django.contrib.admin`
`INSTALLED_APPS`-da olmalıdır).

### Django olmayan mühitdə

`BaseLogger` və `ViewLogger` Django quraşdırılmasa belə işləyir —
`models.py` yalnız `db_log=True` olanda, məhz o an import edilir. Əgər
Django yoxdursa və ya `django_view_logger` `INSTALLED_APPS`-a əlavə
edilməyibsə, DB yazma cəhdi səssizcə keçilir, proqram çökmür, terminal
logu isə normal davam edir.

---

## 9. Reusability qeydləri

- Modul daxilində heç bir konkret layihəyə aid import yoxdur
  (`from accounts.models import ...` kimi importlar qadağandır və
  istifadə edilməyib).
- İstifadəçi məlumatı `getattr(request, "user", None)` ilə generic
  şəkildə alınır, ona görə custom User modelləri ilə problemsiz işləyir.
- Bütün məlumatlar parametr və ya `request` obyekti üzərindən alınır,
  heç bir global state və ya Django settings-dən asılılıq yoxdur.
