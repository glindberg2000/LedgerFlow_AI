from django.db import connection

table_name = "profiles_transactionclassification"
with connection.cursor() as cursor:
    cursor.execute(f"SELECT to_regclass('public.{table_name}');")
    result = cursor.fetchone()
    if result and result[0]:
        print(f"Table '{table_name}' exists.")
    else:
        print(f"Table '{table_name}' DOES NOT exist.")
