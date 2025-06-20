# Generated by Django 5.1.7 on 2025-06-14 14:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('information', '0002_remove_information_information_information_dietgoal_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='information',
            name='dietGoal',
        ),
        migrations.RemoveField(
            model_name='information',
            name='exerciseTime',
        ),
        migrations.RemoveField(
            model_name='information',
            name='exerciseType',
        ),
        migrations.RemoveField(
            model_name='information',
            name='foodType',
        ),
        migrations.RemoveField(
            model_name='information',
            name='mealTime',
        ),
        migrations.AddField(
            model_name='information',
            name='Information',
            field=models.TextField(blank=True, verbose_name='个人简介'),
        ),
        migrations.AlterField(
            model_name='information',
            name='target',
            field=models.TextField(blank=True, verbose_name='目标'),
        ),
    ]
