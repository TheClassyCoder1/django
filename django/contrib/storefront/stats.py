from datetime import date, timedelta

from django.db import connection

from .models import DailySales

PRODUCT_SALES_LIMIT = 10


def get_daily_sales_table_name():
    return DailySales._meta.db_table


def get_average_daily_sales_per_product(category, limit=PRODUCT_SALES_LIMIT):
    """Average daily units sold per product in a category over two weeks."""
    since = date.today() - timedelta(days=13)

    query = f"""
SELECT product_id,
CAST(ROUND(AVG(quantity)) AS INTEGER) AS adu
FROM {get_daily_sales_table_name()}
WHERE category_id = %s
AND sale_date >= %s
GROUP BY product_id
ORDER BY adu DESC
LIMIT {limit}"""

    with connection.cursor() as cursor:
        cursor.execute(query, [category.pk, since])
        return cursor.fetchall()
