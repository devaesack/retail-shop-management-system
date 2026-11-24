import psycopg2

def get_connection():

    conn = psycopg2.connect(
        host="localhost",
        database="retail_shop_db",
        user="postgres",
        password="Esack 77"
    )

    return conn