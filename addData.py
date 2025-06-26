from init_db import conn
import sqlite3

conn = sqlite3.connect("ecommerce.db")
cursor = conn.cursor()

cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Alice Johnson", "alice@example.com"))
cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Bob Smith", "bob@example.com"))
cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Carol Williams", "carol@example.com"))
cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Dave Thompson", "dave@example.com"))
cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Eve Anderson", "eve@example.com"))

cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("Laptop", 1200.00))
cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("Smartphone", 800.00))
cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("Headphones", 150.00))
cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("Monitor", 300.00))
cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("Keyboard", 75.00))
cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("Mouse", 50.00))

cursor.execute("INSERT INTO orders (user_id, amount, date) VALUES (?, ?, ?)", (1, 1200.00, "2024-01-15"))
cursor.execute("INSERT INTO orders (user_id, amount, date) VALUES (?, ?, ?)", (2, 950.00, "2024-02-10"))
cursor.execute("INSERT INTO orders (user_id, amount, date) VALUES (?, ?, ?)", (1, 300.00, "2024-03-05"))
cursor.execute("INSERT INTO orders (user_id, amount, date) VALUES (?, ?, ?)", (3, 75.00, "2024-03-12"))
cursor.execute("INSERT INTO orders (user_id, amount, date) VALUES (?, ?, ?)", (4, 800.00, "2024-04-01"))
cursor.execute("INSERT INTO orders (user_id, amount, date) VALUES (?, ?, ?)", (5, 150.00, "2024-04-15"))
cursor.execute("INSERT INTO orders (user_id, amount, date) VALUES (?, ?, ?)", (2, 1300.00, "2024-05-01"))
cursor.execute("INSERT INTO orders (user_id, amount, date) VALUES (?, ?, ?)", (3, 50.00, "2024-06-10"))


conn.commit()
conn.close()
