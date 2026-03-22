# This file is a part of IntelOwl https://github.com/intelowlproject/IntelOwl
# See the file 'LICENSE' for copying permission.

from django.db import IntegrityError, migrations, transaction


def migrate(apps, schema_editor):
    PlaybookConfig = apps.get_model("playbooks_manager", "PlaybookConfig")
    for playbook in PlaybookConfig.objects.filter(name="Dns"):
        playbook.name = "DNS"
        try:
            with transaction.atomic():
                playbook.save(update_fields=["name"])
        except IntegrityError:
            # Another playbook with the same owner already uses "DNS".
            # Keep this row unchanged to avoid breaking the migration.
            continue


def reverse_migrate(apps, schema_editor):
    PlaybookConfig = apps.get_model("playbooks_manager", "PlaybookConfig")
    for playbook in PlaybookConfig.objects.filter(name="DNS"):
        playbook.name = "Dns"
        try:
            with transaction.atomic():
                playbook.save(update_fields=["name"])
        except IntegrityError:
            # Another playbook with the same owner already uses "Dns".
            # Keep this row unchanged to avoid breaking the migration.
            continue


class Migration(migrations.Migration):
    dependencies = [
        ("playbooks_manager", "0066_link_crawl_visualizer_to_playbook"),
    ]

    operations = [
        migrations.RunPython(migrate, reverse_migrate),
    ]
