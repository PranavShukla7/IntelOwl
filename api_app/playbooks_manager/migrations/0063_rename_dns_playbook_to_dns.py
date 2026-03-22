# This file is a part of IntelOwl https://github.com/intelowlproject/IntelOwl
# See the file 'LICENSE' for copying permission.

from django.db import migrations


def migrate(apps, schema_editor):
    PlaybookConfig = apps.get_model("playbooks_manager", "PlaybookConfig")
    PlaybookConfig.objects.filter(name="Dns").update(name="DNS")


def reverse_migrate(apps, schema_editor):
    PlaybookConfig = apps.get_model("playbooks_manager", "PlaybookConfig")
    PlaybookConfig.objects.filter(name="DNS").update(name="Dns")


class Migration(migrations.Migration):
    dependencies = [
        ("playbooks_manager", "0066_link_crawl_visualizer_to_playbook"),
    ]

    operations = [
        migrations.RunPython(migrate, reverse_migrate),
    ]
