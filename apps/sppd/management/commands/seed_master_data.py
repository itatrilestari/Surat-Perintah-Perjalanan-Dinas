from decimal import Decimal
from django.core.management.base import BaseCommand

from sppd.models import SBMMaster, DailyAllowanceRate, Province, Destination, Transportation, BudgetAccount, TravelPurpose, PaguSPPD
import pandas as pd
from pathlib import Path

SBM_DATA = [
    {"grade": "A", "description": "Pejabat Negara, Eselon I dan II",
     "lodging_limit": Decimal("11600000"), "representation_allowance": Decimal("250000")},
    {"grade": "B", "description": "Eselon III dan Golongan IV",
     "lodging_limit": Decimal("9000000"), "representation_allowance": None},
    {"grade": "C", "description": "Golongan III",
     "lodging_limit": Decimal("7300000"), "representation_allowance": None},
    {"grade": "D", "description": "Golongan I dan II",
     "lodging_limit": Decimal("5600000"), "representation_allowance": None},
]

DAILY_RATES = [
    ("Aceh", Decimal("360000")),
    ("Bali", Decimal("480000")),
    ("Banten", Decimal("370000")),
    ("Bengkulu", Decimal("380000")),
    ("DI Yogyakarta", Decimal("420000")),
    ("DKI Jakarta", Decimal("530000")),
    ("Gorontalo", Decimal("370000")),
    ("Jambi", Decimal("370000")),
    ("Jawa Barat", Decimal("430000")),
    ("Jawa Tengah", Decimal("370000")),
    ("Jawa Timur", Decimal("410000")),
    ("Kalimantan Barat", Decimal("380000")),
    ("Kalimantan Selatan", Decimal("380000")),
    ("Kalimantan Tengah", Decimal("360000")),
    ("Kalimantan Timur", Decimal("430000")),
    ("Kalimantan Utara", Decimal("430000")),
    ("Kepulauan Bangka Belitung", Decimal("410000")),
    ("Kepulauan Riau", Decimal("370000")),
    ("Lampung", Decimal("380000")),
    ("Maluku", Decimal("380000")),
    ("Maluku Utara", Decimal("430000")),
    ("Nusa Tenggara Barat", Decimal("440000")),
    ("Nusa Tenggara Timur", Decimal("430000")),
    ("Papua", Decimal("580000")),
    ("Papua Barat Daya", Decimal("480000")),
    ("Riau", Decimal("370000")),
    ("Sulawesi Selatan", Decimal("430000")),
    ("Sulawesi Tengah", Decimal("370000")),
    ("Sulawesi Tenggara", Decimal("380000")),
    ("Sulawesi Utara", Decimal("370000")),
    ("Sumatera Barat", Decimal("380000")),
    ("Sumatera Selatan", Decimal("380000")),
    ("Sumatera Utara", Decimal("370000")),
]

TRANSPORTATION = [
    {"code": "KL", "name": "Kapal Laut", "via": "Sea"},
    {"code": "KD", "name": "Kendaraan Dinas", "via": "Land"},
    {"code": "KU", "name": "Kendaraan Umum", "via": "Land"},
    {"code": "KA", "name": "Kereta Api", "via": "Land"},
    {"code": "PSW", "name": "Pesawat Udara", "via": "Air"},
]

BUDGET_ACCOUNT = [
    {"code": "524111", "name":"Belanja Perjalanan Dinas Biasa"}
]

TRAVEL_PURPOSE = [
    {"name": "Bimbingan Teknis Aparatur"},
    {"name": "Kunjungan Kerja"},
    {"name": "Monitoring & Evaluasi Program"},
    {"name": "Pendidikan & Pelatihan"},
    {"name": "Rapat Koordinasi Nasional"},
    {"name": "Sosialisasi Kebijakan"},
]

PAGU = [
    {"working_unit_id": "9c13b8d8-b98c-4570-872e-0090e133ac2f", "working_unit_name": "Coofis Corporation", "working_unit_code": "0100000000", "working_unit_level":"0", "pagu": "750000000"}
]

class Command(BaseCommand):
    help = "Seed data SBM dan uang harian"

    def handle(self, *args, **options):
        self.seed_regions()
        self.seed_sbm()
        self.seed_daily_rates()
        self.seed_transportation()
        self.seed_budget_account()
        self.seed_travel_purpose()
        self.seed_pagu()

        self.stdout.write(
            self.style.SUCCESS(
                "Semua seed data SPPD berhasil diproses."
            )
        )

    def seed_regions(self):
        BASE_DIR = Path(__file__).resolve().parents[4]
        file_path = BASE_DIR / "data" / "daftar_kota_provinsi.xlsx"

        df = pd.read_excel(
            file_path,
            sheet_name="Daftar Kota",
            dtype=str,
        )

        df = df[
            ["Provinsi", "Nama Kota", "Kategori"]
        ].dropna(
            subset=["Provinsi", "Nama Kota"]
        )

        # Normalisasi whitespace
        for column in ["Provinsi", "Nama Kota", "Kategori"]:
            df[column] = df[column].str.strip()

        province_names = df["Provinsi"].unique()

        # Seed Province
        for province_name in province_names:
            Province.objects.get_or_create(
                name=province_name,
            )

        provinces = {
            province.name: province
            for province in Province.objects.filter(
                name__in=province_names
            )
        }

        # Seed Destination
        for _, row in df.iterrows():
            Destination.objects.update_or_create(
                name=row["Nama Kota"],
                province=provinces[row["Provinsi"]],
                defaults={
                    "category": row["Kategori"],
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Regions selesai: {len(province_names)} provinsi, "
                f"{len(df)} kabupaten/kota."
            )
        )

    def seed_sbm(self):
        for row in SBM_DATA:
            SBMMaster.objects.update_or_create(
                grade=row["grade"],
                defaults={
                    "description": row["description"],
                    "lodging_limit": row["lodging_limit"],
                    "representation_allowance": row[
                        "representation_allowance"
                    ],
                },
            )

        self.stdout.write(
            self.style.SUCCESS("SBM Master selesai.")
        )

    def seed_daily_rates(self):
        for province_name, amount in DAILY_RATES:
            province = Province.objects.filter(
                name__iexact=province_name
            ).first()

            if not province:
                self.stdout.write(
                    self.style.WARNING(
                        f"Provinsi '{province_name}' tidak ditemukan."
                    )
                )
                continue

            DailyAllowanceRate.objects.update_or_create(
                province=province,
                defaults={
                    "amount": amount,
                },
            )

        self.stdout.write(
            self.style.SUCCESS("Daily Allowance Rate selesai.")
        )

    def seed_transportation(self):
        for row in TRANSPORTATION:
            Transportation.objects.update_or_create(
                code=row["code"],
                defaults={
                    "name": row["name"],
                    "via": row["via"],
                },
            )

        self.stdout.write(
            self.style.SUCCESS("Transportation selesai.")
        )

    def seed_budget_account(self):
        for row in BUDGET_ACCOUNT:
            BudgetAccount.objects.update_or_create(
                code=row["code"],
                defaults={
                    "name": row["name"],
                },
            )

        self.stdout.write(
            self.style.SUCCESS("Budget Account selesai.")
        )

    def seed_travel_purpose(self):
        for row in TRAVEL_PURPOSE:
            TravelPurpose.objects.update_or_create(
                name=row["name"],
            )

        self.stdout.write(
            self.style.SUCCESS("Travel Purpose selesai.")
        )

    def seed_pagu(self):
        for row in PAGU:
            PaguSPPD.objects.update_or_create(
                pagu=row["pagu"],
                working_unit_id=row["working_unit_id"],
                working_unit_name=row["working_unit_name"],
                working_unit_code=row["working_unit_code"],
                working_unit_level=row["working_unit_level"],
            )

        self.stdout.write(
            self.style.SUCCESS("Pagu selesai.")
        )