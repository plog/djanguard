# Generated by Django 5.1.2 on 2024-10-22 06:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0025_userkey'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='telegram_bot_token',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='telegram_chat_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
