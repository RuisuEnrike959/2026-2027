from django.db import migrations


def create_api_staff_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.using(schema_editor.connection.alias).get_or_create(name="API Staff")


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("library", "0002_book_cover_image_book_show_on_home"),
    ]

    operations = [
        migrations.RunPython(create_api_staff_group, migrations.RunPython.noop),
    ]
