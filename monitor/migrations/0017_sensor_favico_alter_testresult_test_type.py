# Generated by Django 5.1.2 on 2024-10-13 08:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0016_alter_action_selenium_script'),
    ]

    operations = [
        migrations.AddField(
            model_name='sensor',
            name='favico',
            field=models.CharField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='testresult',
            name='test_type',
            field=models.CharField(choices=[('status_code', 'Status Code'), ('contains_keyword', 'Contains Keyword'), ('selenium', 'Selenium Style'), ('json_key_exists', 'JSON Key Exists')], max_length=100),
        ),
    ]
