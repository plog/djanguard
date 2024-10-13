# Generated by Django 5.1.2 on 2024-10-13 02:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0012_rename_request_body_action_payload'),
    ]

    operations = [
        migrations.AlterField(
            model_name='action',
            name='assertion_type',
            field=models.CharField(choices=[('status_code', 'Status Code'), ('contains_keyword', 'Contains Keyword'), ('selenium', 'Selenium Style'), ('json_key_exists', 'JSON Key Exists')], default='status_code', max_length=50),
        ),
    ]
