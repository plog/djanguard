# Generated by Django 5.1.2 on 2024-10-16 10:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0023_alter_action_selenium_script'),
    ]

    operations = [
        migrations.AlterField(
            model_name='action',
            name='assertion_type',
            field=models.CharField(choices=[('status_code', 'Status Code'), ('contains_keyword', 'Contains Keyword'), ('selenium', 'Selenium Style'), ('screenshot', 'Take a screenshot'), ('json_key_exists', 'JSON Key Exists')], default='status_code', max_length=50),
        ),
        migrations.AlterField(
            model_name='testresult',
            name='test_type',
            field=models.CharField(choices=[('status_code', 'Status Code'), ('contains_keyword', 'Contains Keyword'), ('selenium', 'Selenium Style'), ('screenshot', 'Take a screenshot'), ('json_key_exists', 'JSON Key Exists')], max_length=100),
        ),
    ]