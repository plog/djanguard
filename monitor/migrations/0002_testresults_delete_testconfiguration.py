# Generated by Django 5.1.2 on 2024-10-09 12:29

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestResults',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('test_type', models.CharField(choices=[('status_code', 'Status Code'), ('keyword', 'Keyword in Body'), ('response_time', 'Response Time')], max_length=100)),
                ('expected_value', models.CharField(help_text='Expected value for this test', max_length=100)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('action', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tests', to='monitor.action')),
            ],
        ),
        migrations.DeleteModel(
            name='TestConfiguration',
        ),
    ]
