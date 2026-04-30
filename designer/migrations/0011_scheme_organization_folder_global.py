from django.db import migrations, models


def make_existing_folders_global(apps, schema_editor):
    Folder = apps.get_model('designer', 'Folder')
    Folder.objects.update(org=None)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('designer', '0010_alter_auditlog_options_alter_folder_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='folder',
            name='org',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name='folders',
                to='designer.organization',
                verbose_name='Организация',
            ),
        ),
        migrations.AddField(
            model_name='scheme',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name='schemes',
                to='designer.organization',
                verbose_name='Организация',
            ),
        ),
        migrations.RunPython(make_existing_folders_global, noop_reverse),
    ]
