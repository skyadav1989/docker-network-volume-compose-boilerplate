import os
import time

import pymysql
from flask import Flask, jsonify

app = Flask(__name__)

def get_connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        connect_timeout=3,
        cursorclass=pymysql.cursors.DictCursor,
    )

def initialize_database():
    # Retry briefly in case MySQL is still initializing.
    for attempt in range(15):
        try:
            connection = get_connection()
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS products (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            name VARCHAR(100) NOT NULL
                        )
                    """)
                    cursor.execute("""
                        INSERT INTO products (name)
                        SELECT 'Docker Compose Demo'
                        WHERE NOT EXISTS (
                            SELECT 1 FROM products
                        )
                    """)
                connection.commit()
            return
        except pymysql.MySQLError:
            if attempt == 14:
                raise
            time.sleep(2)

@app.get("/")
def home():
    return jsonify(
        message="Docker Compose API is running",
        endpoints=["/health", "/products"]
    )

@app.get("/health")
def health():
    try:
        connection = get_connection()
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 AS ok")
                cursor.fetchone()
        return jsonify(status="healthy", database="connected"), 200
    except pymysql.MySQLError:
        return jsonify(status="unhealthy", database="disconnected"), 503

@app.get("/products")
def products():
    connection = get_connection()
    with connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, name FROM products ORDER BY id")
            rows = cursor.fetchall()
    return jsonify(rows)

if __name__ == "__main__":
    initialize_database()
    app.run(host="0.0.0.0", port=5000)
