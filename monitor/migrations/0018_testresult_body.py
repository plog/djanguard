# Generated by Django 5.1.2 on 2024-10-13 09:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0017_sensor_favico_alter_testresult_test_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='testresult',
            name='body',
            field=models.CharField(default=1, help_text='Add more context to the results', max_length=255),
            preserve_default=False,
        ),
    ]