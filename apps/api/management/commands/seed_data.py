
import csv
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from api.models import Profile, WorkingUnit

User = get_user_model()

class Command(BaseCommand):
    help = "Load initial seed data from CSV"

    def handle(self, *args, **options):
        seed_dir = Path(settings.BASE_DIR) / "data"

        working_unit_file = seed_dir / "working_units.csv"
        profile_file = seed_dir / "profiles.csv"

        if not working_unit_file.exists() or not profile_file.exists():
            raise CommandError("Seed CSV files not found.")

        with transaction.atomic():
            self.load_working_units(working_unit_file)
            self.load_profiles(profile_file)

        self.stdout.write(self.style.SUCCESS("Seed data successfully loaded."))

    def load_working_units(self, file_path):
        self.stdout.write("Loading Working Units...")

        with open(file_path, mode="r", encoding="utf-8-sig") as file:
            rows = list(csv.DictReader(file))

        pending = {row["code"]: row for row in rows}
        created = 0
        updated = 0

        while pending:
            processed = []
            for code, row in pending.items():
                parent_code = row.get("parent_code", "").strip()

                parent = None
                if parent_code:
                    parent = WorkingUnit.objects.filter(code=parent_code).first()
                    if not parent:
                        continue

                obj, is_created = WorkingUnit.objects.update_or_create(
                    code=code,
                    defaults={
                        "name": row["name"].strip(),
                        "level": int(row["level"]),
                        "parent": parent,
                    },
                )

                if is_created:
                    created += 1
                else:
                    updated += 1

                processed.append(code)

            if not processed:
                raise CommandError(
                    "Working Unit tree invalid. "
                    f"Check parent_code for: {list(pending.keys())}"
                )

            for code in processed:
                del pending[code]

        self.stdout.write(self.style.SUCCESS(f"Working Units: {created} created, {updated} updated."))

    def load_profiles(self, file_path):
        self.stdout.write("Loading Users and Profiles...")

        with open(file_path, mode="r", encoding="utf-8-sig") as file:
            rows = csv.DictReader(file)

            created = 0
            updated = 0

            for row in rows:
                username = row["username"].strip()
                password = row["password"].strip()

                user, user_created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": row["email"].strip(),
                    },
                )

                if not user_created:
                    user.email = row["email"].strip()

                user.set_password(password)
                user.save()

                working_unit_code = row.get("working_unit_code", "").strip()
                working_unit = None

                if working_unit_code:
                    working_unit = WorkingUnit.objects.filter(code=working_unit_code).first()

                    if not working_unit:
                        raise CommandError(
                            f"Working Unit {working_unit_code} not found."
                        )

                _, profile_created = Profile.objects.update_or_create(
                    nik=row["nik"].strip(),
                    defaults={
                        "name": row["name"].strip(),
                        "phone": row["phone"].strip(),
                        "email": row["email"].strip(),
                        "gender": row["gender"].strip(),
                        "working_unit": working_unit,
                        "user": user
                    },
                )

                if profile_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(f"Profiles: {created} created, {updated} updated."))
