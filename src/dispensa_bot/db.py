import os

import pymysql
import re 
from decimal import Decimal
from dotenv import load_dotenv


# Carica le variabili dal file .env
load_dotenv()





class DispensaDB:
    def __init__(self):
        self.host = os.getenv("MYSQL_HOST")
        self.port = int(os.getenv("MYSQL_PORT", 3306))
        self.user = os.getenv("MYSQL_USER")
        self.password = os.getenv("MYSQL_PASSWORD")
        self.database = os.getenv("MYSQL_DATABASE")
# Crea una connessione al database MySQL
    def get_connection(self):
        return pymysql.connect(
        host=self.host,
        port=self.port,
        user=self.user,
        password=self.password,
        database=self.database,
        cursorclass=pymysql.cursors.DictCursor,
    )


    # Test veloce per verificare che Python riesca a collegarsi a MySQL
    def test_connection(self):
        connection = self.get_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 AS ok")
                result = cursor.fetchone()
                return result

        finally:
            connection.close()

    # Aggiunge un prodotto alla tabella items
    def add_item(self,item: dict):
        connection = self.get_connection()

        quantity = self.clean_quantity(item.get("quantity"))

        unit = item.get("unit")
        if quantity is None:
            quantity = 1
            unit = unit or "pacco"
        try:
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO items
                    (name, quantity, unit, location, expiry_date, notes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """

                cursor.execute(
                    sql,
                    (
                        item.get("name"),
                        quantity,
                        unit,
                        item.get("location"),
                        item.get("expiry_date"),
                        item.get("notes"),
                    ),
                )

            connection.commit()

        finally:
            connection.close()

    def list_items(self,location: str | None = None):
        conn = self.get_connection()

        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                if location:
                    sql = """
                        SELECT id, name, quantity, unit, location, expiry_date, notes
                        FROM items
                        WHERE location = %s
                        ORDER BY created_at DESC
                    """
                    cursor.execute(sql, (location,))
                else:
                    sql = """
                        SELECT id, name, quantity, unit, location, expiry_date, notes
                        FROM items
                        ORDER BY created_at DESC
                    """
                    cursor.execute(sql)

                return cursor.fetchall()

        finally:
            conn.close()
            
    def format_items(self,rows):
        if not rows:
            return "Non ho trovato prodotti."

        lines = ["📦 Prodotti trovati:"]

        for row in rows:
            name = row["name"]
            quantity = row.get("quantity")
            unit = row.get("unit") or ""
            location = row.get("location") or "altro"
            expiry = row.get("expiry_date")

            qty_text = ""
            if quantity is not None:
                qty_text = f" - {quantity:g} {unit}".strip()

            expiry_text = ""
            if expiry:
                expiry_text = f" - scade il {expiry}"

            lines.append(f"• {name}{qty_text} ({location}){expiry_text}")

        return "\n".join(lines)

    def delete_all_items(self):
        conn = self.get_connection()

        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM items")
                deleted_count = cursor.rowcount

            conn.commit()
            return deleted_count

        finally:
            conn.close()
            
    def clean_quantity(self, value):
        if value is None or value == "":
            return None

        if isinstance(value, (int, float,Decimal)):
            return float(value)

        if isinstance(value, str):
            value = value.replace(",", ".")
            match = re.search(r"\d+(\.\d+)?", value)

            if match:
                return float(match.group())

        return None
    
        
    def consume_item(self, item: dict, amount_fraction=None):
        conn = self.get_connection()

        name = item.get("name")
        quantity_to_remove = self.clean_quantity(item.get("quantity"))

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, name, quantity, unit
                    FROM items
                    WHERE name LIKE %s
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (f"%{name}%",),
                )

                row = cursor.fetchone()

                if not row:
                    return f"Non ho trovato {name}."

                current_quantity = self.clean_quantity(row.get("quantity"))

                if current_quantity is None:
                    return f"{row['name']} non ha una quantità valida."

                if amount_fraction is not None:
                    remove_quantity = current_quantity * float(amount_fraction)
                elif quantity_to_remove is not None:
                    remove_quantity = quantity_to_remove
                else:
                    return f"Non ho capito quanto togliere da {row['name']}."

                new_quantity = current_quantity - remove_quantity

                unit = (row.get("unit") or "").lower()
                
                if(
                    new_quantity <= 0
                    or unit in ["grammo", "grammi", "g", "gr"] and new_quantity <= 30
                    or unit in ["kg", "chilo", "chili", "chilogrammo", "chilogrammi"] and new_quantity <= 0.03
                    or unit in ["litro", "litri", "l"] and new_quantity <= 0.05
                    or unit in ["pacco", "pacchi"] and new_quantity <= 0.05
                ):
                    new_quantity = 0

                cursor.execute(
                    """
                    UPDATE items
                    SET quantity = %s
                    WHERE id = %s
                    """,
                    (new_quantity, row["id"]),
                )

            conn.commit()

            return f"Ho aggiornato {row['name']}: da {current_quantity:g} a {new_quantity:g} {row.get('unit') or ''}."

        finally:
            conn.close()