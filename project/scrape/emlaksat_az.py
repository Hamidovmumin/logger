import json
from bs4 import BeautifulSoup
from datetime import datetime
import sys
import django
import re
import requests
import os
from urllib.parse import urlparse
from django.core.files.base import ContentFile
import time

# # 1. 'project' qovluğunun tam yolunu tapıb sys.path-ə əlavə edirik:
# # (Bu, 'config' və 'properties' kimi modulların rahat tapılmasını təmin edir)
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# if BASE_DIR not in sys.path:
#     sys.path.append(BASE_DIR)
#
# # 2. Settings modulunu göstəririk
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
#
# # 3. Django-nu başladırıq
# django.setup()

from properties.models import Category, PropertyImage,City,Area
from crud.property import category_crud, property_crud


def normalize_text(text: str) -> str:
    if not text:
        return ""

    # 1. Bütün hərfləri kiçik hərfə çeviririk
    text = text.lower()

    # 2. Xüsusi simvolların (/ , - və s.) ətrafındakı artıq boşluqları təmizləyirik
    text = re.sub(r'\s*/\s*', '/', text)  # " / " -> "/"
    text = re.sub(r'\s*-\s*', '-', text)  # " - " -> "-"

    # 3. Mətnin daxilindəki çoxlu boşluqları tək boşluqla əvəzləyirik ("  " -> " ")
    text = re.sub(r'\s+', ' ', text)

    # 4. Tez-tez səhv yazılan söz və ya hərf əvəzləmələri:
    replacements = {
        # Söz səviyyəsində təmizləmə
        "həyet": "həyət",
        "heyet": "həyət",
        "temirli": "təmirli",
        "temirsiz": "təmirsiz",
        "kuqca": "kupça",
        "kupca": "kupça",

        # Hərf səviyyəsində eyniləşdirmə (əgər e/ə fərqini tam aradan qaldırmaq istəyirsinizsə)
        # "e": "ə",
    }

    for word, target in replacements.items():
        # Söz sərhədlərini nəzərə alaraq dəyişirik (bütün sözü uyğunlaşdırır)
        text = re.sub(r'\b' + word + r'\b', target, text)

    # 5. Başda və sonda olan boşluqları silirik
    return text.strip()


def safe_int(value, default=None):
    if not value:
        return default
    try:
        return int(str(value).strip())
    except ValueError:
        return default


def extract_number(text: str, default: int = 0) -> int:

    if not text:
        return default

    # Mətndəki bütün rəqəm bloklarını tapıb birlaşdiririk
    numbers = "".join(re.findall(r'\d+', str(text)))

    if numbers:
        return int(numbers)

    return default


def has_kupcha(text: str) -> bool:
    if not text:
        return False

    # Regex ilə hem 'ç' hem 'c' variantını hərf həssaslığı olmadan (IGNORECASE) axtarırıq
    pattern = r'kup[çc]a'

    return bool(re.search(pattern, text, re.IGNORECASE))


def download_image_file(image_url):
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Şəkil yüklənmədi: {image_url} - {e}")
        return None

    filename = os.path.basename(urlparse(image_url).path)
    return ContentFile(response.content, name=filename)


def save_property_images(prop, imgs, skip_keys=None):
    skip_keys = skip_keys or []
    for order, url in imgs.items():
        if order in skip_keys:
            continue

        image_file = download_image_file(url)
        if not image_file:
            continue

        PropertyImage.objects.create(
            prop=prop,
            image=image_file,
            is_allowed=False,
            # is_cover-a toxunmuruq — modelin öz save() metodu
            # ilk PropertyImage üçün onu avtomatik True edəcək
        )


def save(properties):
    categories = list(Category.objects.all())

    for i in range(len(properties)):
        prop_data = properties[i].get('data', {})
        imgs = properties[i].get('imgs', {})

        emlak_novu = prop_data.get("Əmlak növü")
        matched_category = None

        if emlak_novu:
            cleaned_target = normalize_text(emlak_novu)

            for cat in categories:
                if normalize_text(cat.name) == cleaned_target:
                    matched_category = cat
                    break

            # Əgər bazada tapılmadısa, yeni kateqoriya yaradırıq və siyahımıza əlavə edirik
            if not matched_category:
                matched_category = category_crud.create(name=emlak_novu)
                categories.append(matched_category)
                print(f"'{emlak_novu}' yeni kateqoriya kimi əlavə edildi.")

        # 2. Elan məlumatlarını götürürük
        elan_novu = prop_data.get("Elan növü", "")
        temir_veziyyeti = prop_data.get("Təmir vəziyyəti", "")
        raw_floor = prop_data.get("Mərtəbə sayı")
        floor = prop_data.get("Yerləşdiyi mərtəbə")
        room_count = prop_data.get("Otaq sayı")
        square = prop_data.get("Sahəsi")
        kupca = prop_data.get("Əmlak sənədi")
        name = prop_data.get("Elan adı")
        qiymet = prop_data.get('Qiymət')
        phone = prop_data.get('Telefon')
        city_name = prop_data.get('Şəhər')
        area_name = prop_data.get('Rayon')

        # İlk şəkli (key="1") yükləyirik
        first_img_url = imgs.get("1")
        image_file = download_image_file(first_img_url) if first_img_url else None

        city_obj = None
        area_obj = None

        if city_name:
            city_obj, _ = City.objects.get_or_create(
                name=city_name.strip()
            )

            # 2. Şəhər məlumdursa, həmin şəhərə bağlı Rayonu tapırıq və ya yaradırıq
            if area_name:
                area_obj, _ = Area.objects.get_or_create(
                    city=city_obj,
                    name=area_name.strip()
                )

        # 3. Property obyektini yaradırıq
        new_property = property_crud.create(
            name=name,
            is_sale=(elan_novu.lower() == 'satılır'),
            category=matched_category,
            is_renovated=(normalize_text(temir_veziyyeti) == 'təmirli'),
            floor_s=safe_int(raw_floor),
            floor=safe_int(floor),
            room_count=safe_int(room_count),
            square=extract_number(square),
            has_extract=has_kupcha(kupca),
            price=extract_number(qiymet),
            image=image_file,
            phone=phone,
            city=city_obj,
            area = area_obj,
            is_scraped=True
        )

        save_property_images(new_property, imgs, skip_keys=["1"])

        print(f'{i+1}-ci data uğurla yükləndi ✅')

    return


def scrape_properties_url():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        "https://emlaksat.az/search",
        headers=headers
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    properties = []

    articles = soup.find_all("article", class_="estate-item")

    for article in articles:
        a = article.find("a", href=True)

        if not a:
            continue

        detail_url = a["href"]

        properties.append({
            "url": detail_url
        })

    print(f"Tapılan URL sayı: {len(properties)}")

    return properties


def scrape_properties_detail(properties, headers):
    all_details = []  # 1. DÜZƏLİŞ: Yeni siyahı yaradırıq

    for prop in properties:
        detail_response = requests.get(prop["url"], headers=headers)
        detail_soup = BeautifulSoup(detail_response.text, "html.parser")

        detail_data = {}

        # Elan adı
        title = detail_soup.find("h1", class_="font-bold")
        if title:
            detail_data["Elan adı"] = title.get_text(strip=True)

        # Qiymət
        price = detail_soup.find("div", class_=lambda c: c and "text-2xl" in c)
        if price:
            detail_data["Qiymət"] = price.get_text(strip=True)

        # Şəhər və Rayon
        location = detail_soup.find(
            "div", class_=lambda c: c and "divide-x" in c
        )
        if location:
            locations = [
                div.get_text(strip=True)
                for div in location.find_all("div", recursive=False)
            ]
            if len(locations) >= 2:
                detail_data["Şəhər"] = locations[1]
            if len(locations) >= 3:
                detail_data["Rayon"] = locations[2]

        # Telefon
        phone_div = detail_soup.find(
            "div", class_=lambda c: c and "js-phone-list-estate-view" in c
        )
        if phone_div:
            phone = phone_div.find(
                "a", href=lambda h: h and h.startswith("tel:")
            )
            if phone:
                detail_data["Telefon"] = phone.get_text(strip=True)

        # Digər məlumatlar
        for div in detail_soup.find_all(
            "div", class_=lambda c: c and "items-center" in c
        ):
            spans = div.find_all("span", recursive=False)
            if len(spans) != 2:
                continue

            key = spans[0].get_text(strip=True)
            value = spans[1].get_text(strip=True)
            detail_data[key] = value

        # Şəkillər
        imgs = {}
        slider = detail_soup.find("div", id="estateSlider")
        if slider:
            index = 1
            for img in slider.find_all("img"):
                src = img.get("src")
                if not src:
                    continue
                imgs[str(index)] = src
                index += 1

        # 2. DÜZƏLİŞ: Məlumatı yeni siyahıya yığırıq
        all_details.append(
            {"url": prop["url"], "data": detail_data, "imgs": imgs}
        )

        # Serveri yükləməmək üçün qısa pauza
        time.sleep(1)

    print(json.dumps(all_details, ensure_ascii=False, indent=4))
    return all_details


# if __name__ == "__main__":
#     print("Saytdan datalar götürülür...")
#     properties = scrape_properties_url()
#
#     print('#########################################################################')
#     print(f'Saytdan {len(properties)} sayda data götürüldü ✅')
    # print("Bütün datalar Database-yə yazılır...")
    #
    # save(properties)
    #
    # print("Hamısı uğurla bitdi.")