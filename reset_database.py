import pymysql

# Veritabanı bağlantısı
connection = pymysql.connect(
    host='localhost',
    user='root',
    password='3184156'
)

try:
    with connection.cursor() as cursor:
        # Veritabanını sil ve yeniden oluştur
        cursor.execute("DROP DATABASE IF EXISTS mydb")
        cursor.execute("CREATE DATABASE mydb")
        print("Veritabanı başarıyla sıfırlandı!")

except Exception as e:
    print(f"Hata oluştu: {e}")

finally:
    connection.close() 