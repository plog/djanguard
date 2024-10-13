# Generated by Django 5.1.2 on 2024-10-13 03:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0013_alter_action_assertion_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='action',
            name='selector',
        ),
        migrations.AddField(
            model_name='action',
            name='selenium_script',
            field=models.CharField(blank=True, help_text='Selenium Style script)', max_length=200, null=True),
        ),
    ]
