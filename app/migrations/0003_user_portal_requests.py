import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0002_user_last_login"),
    ]

    operations = [
        migrations.RenameField(
            model_name="borrowrequest",
            old_name="reason",
            new_name="purpose",
        ),
        migrations.AddField(
            model_name="borrowrequest",
            name="due_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="borrowrequest",
            name="status",
            field=models.IntegerField(
                choices=[
                    (1, "Pending"),
                    (2, "Approved"),
                    (3, "Issued"),
                    (4, "Partially Returned"),
                    (5, "Returned"),
                    (6, "Rejected"),
                    (0, "Cancelled"),
                ],
                default=1,
            ),
        ),
        migrations.AlterField(
            model_name="borrowrequest",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="borrow_requests",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="equipmentunit",
            name="catalog_item",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="units",
                to="app.catalogitem",
            ),
        ),
        migrations.RemoveField(
            model_name="requestitem",
            name="equipment_unit",
        ),
        migrations.AddField(
            model_name="requestitem",
            name="catalog_item",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="request_items",
                to="app.catalogitem",
            ),
        ),
        migrations.AlterField(
            model_name="requestitem",
            name="catalog_item",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="request_items",
                to="app.catalogitem",
            ),
        ),
        migrations.AlterField(
            model_name="requestitem",
            name="borrow_request",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="items",
                to="app.borrowrequest",
            ),
        ),
        migrations.AlterField(
            model_name="requestitem",
            name="quantity",
            field=models.PositiveIntegerField(
                validators=[django.core.validators.MinValueValidator(1)]
            ),
        ),
        migrations.AlterField(
            model_name="unitallocation",
            name="request_item",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="allocations",
                to="app.requestitem",
            ),
        ),
        migrations.AddConstraint(
            model_name="requestitem",
            constraint=models.UniqueConstraint(
                fields=("borrow_request", "catalog_item"),
                name="unique_catalog_item_per_request",
            ),
        ),
        migrations.AddConstraint(
            model_name="requestitem",
            constraint=models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name="request_item_quantity_gte_1",
            ),
        ),
    ]
