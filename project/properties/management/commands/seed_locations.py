
import os
import json
from django.core.management.base import BaseCommand
from properties.models import City, Area, Village

class Command(BaseCommand):
    help = "rielix_location_data.json faylından coğrafi məlumatları verilənlər bazasına daxil edir"

    def handle(self, *args, **options):
        file_path = 'rielix_location_data.json'

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"Xəta: '{file_path}' faylı kök qovluqda tapılmadı!"))
            return

        self.stdout.write(self.style.WARNING("JSON oxunur və Seeding prosesi başlayır..."))

        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                raw_data = json.load(f)
                data = raw_data.get('data', {})
            except json.JSONDecodeError:
                self.stdout.write(self.style.ERROR("Xəta: JSON faylının daxili formatı səhvdir!"))
                return

        cities_data = data.get('City', [])
        city_counter = 0
        for c in cities_data:
            city_obj, created = City.objects.get_or_create(
                id=c['id'],
                defaults={'name': c['name'].strip()}
            )
            if not created and city_obj.name != c['name'].strip():
                city_obj.name = c['name'].strip()
                city_obj.save()
            city_counter += 1

        self.stdout.write(self.style.SUCCESS(f"-> {city_counter} ədəd Şəhər (City) yoxlanıldı/əlavə edildi."))

        areas_data = data.get('Area', [])
        area_counter = 0
        for a in areas_data:
            city_fk = a['foreign_keys'].get('city', {})
            city_id = city_fk.get('id')

            try:
                city_instance = City.objects.get(id=city_id)
            except City.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Ötürüldü: Rayon '{a['name']}' üçün City ID {city_id} bazada tapılmadı!"))
                continue

            area_obj, created = Area.objects.get_or_create(
                id=a['id'],
                defaults={
                    'name': a['name'].strip(),
                    'city': city_instance
                }
            )
            if not created:
                area_obj.name = a['name'].strip()
                area_obj.city = city_instance
                area_obj.save()
            area_counter += 1

        self.stdout.write(self.style.SUCCESS(f"-> {area_counter} ədəd İnzibati Rayon (Area) yoxlanıldı/əlavə edildi."))

        villages_data = data.get('Village', [])
        village_counter = 0
        for v in villages_data:
            area_fk = v['foreign_keys'].get('area', {})
            area_id = area_fk.get('id')

            try:
                area_instance = Area.objects.get(id=area_id)
            except Area.DoesNotExist:
                continue

            village_obj, created = Village.objects.get_or_create(
                id=v['id'],
                defaults={
                    'name': v['name'].strip(),
                    'area': area_instance
                }
            )
            if not created:
                village_obj.name = v['name'].strip()
                village_obj.area = area_instance
                village_obj.save()
            village_counter += 1

        self.stdout.write(self.style.SUCCESS(f"-> {village_counter} ədəd Qəsəbə/Mikrorayon (Village) yoxlanıldı/əlavə edildi."))
        self.stdout.write(self.style.SUCCESS("Təbrik edirəm! Bütün loqasiya dataları DB-yə uğurla seed olundu."))