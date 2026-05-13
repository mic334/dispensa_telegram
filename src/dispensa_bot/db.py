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
        price = self.clean_price(item.get("price"))
        quantity = self.clean_quantity(item.get("quantity"))
        initial_quantity = quantity
        unit = item.get("unit")
        if quantity is None:
            quantity = 1
            unit = unit or "pacco"
        try:
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO items
                    (name, quantity, initial_quantity, unit, location, expiry_date, notes, price)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                
                cursor.execute(
                    sql,
                    (
                        item.get("name"),
                        quantity,
                        initial_quantity,
                        unit,
                        item.get("location"),
                        item.get("expiry_date"),
                        item.get("notes"),
                        price,
                        
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
                        AND (quantity IS NULL OR quantity > 0)
                        ORDER BY created_at DESC
                    """
                    cursor.execute(sql, (location,))
                else:
                    sql = """
                        SELECT id, name, quantity, unit, location, expiry_date, notes
                        FROM items
                        WHERE quantity IS NULL OR quantity > 0
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
                qty_text = f" - {quantity:g} {unit}"

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

    def clean_price(self, value):
        if value is None:
            return None

        if isinstance(value, Decimal):
            return value

        try:
            if isinstance(value, str):
                value = value.replace(",", ".").strip()

            return Decimal(str(value))
        except:
            return None

            
    
    
    
    
    def get_next_receipt_label(self, chat_id):
        connection = self.get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM receipts
                    WHERE chat_id = %s
                    """,
                    (chat_id,),
                )
                row = cursor.fetchone()
                number = int(row["count"]) + 1
                return f"scontrino {number}"
        finally:
            connection.close()


    def create_receipt(self, chat_id, label=None, total_price=0):
        if label is None:
            label = self.get_next_receipt_label(chat_id)

        connection = self.get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO receipts (chat_id, label, total_price, status)
                    VALUES (%s, %s, %s, 'draft')
                    """,
                    (chat_id, label, total_price),
                )
                receipt_id = cursor.lastrowid
                connection.commit()
                return receipt_id, label
        finally:
            connection.close()


    def add_receipt_line(self, receipt_id, item):
        quantity = self.clean_quantity(item.get("quantity")) or 1
        unit = item.get("unit") or "pezzo"
        price = self.clean_price(item.get("price"))

        unit_price = None
        if price is not None and quantity:
            unit_price = price / Decimal(str(quantity))

        raw_name = item.get("raw_name") or item.get("name") or "prodotto"
        name = item.get("name") or raw_name

        connection = self.get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO receipt_lines
                    (receipt_id, raw_name, name, quantity, unit, line_price, unit_price, needs_review)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        receipt_id,
                        raw_name,
                        name,
                        quantity,
                        unit,
                        price,
                        unit_price,
                        False,
                    ),
                )
                connection.commit()
        finally:
            connection.close()
    
            

    def get_expiring_items(self, days=3):
        try:
            days = int(days)
        except:
            days = 3

        connection = self.get_connection()

        try:
            with connection.cursor() as cursor:
                sql = """
                SELECT *
                FROM items
                WHERE expiry_date IS NOT NULL
                AND expiry_date <= DATE_ADD(CURDATE(), INTERVAL %s DAY)
                AND expiry_date >= CURDATE()
                ORDER BY expiry_date ASC
                """

                cursor.execute(sql, (days,))
                return cursor.fetchall()

        finally:
            connection.close()
            
    def get_pantry_value(self):
        connection = self.get_connection()

        try:
            with connection.cursor() as cursor:
                sql = """
                SELECT
                    SUM(
                        CASE
                            WHEN price IS NOT NULL
                            AND quantity IS NOT NULL
                            AND initial_quantity IS NOT NULL
                            AND initial_quantity > 0
                            THEN price * (quantity / initial_quantity)
                            ELSE 0
                        END
                    ) AS total_value
                FROM items
                WHERE quantity IS NULL OR quantity > 0
                """

                cursor.execute(sql)
                row = cursor.fetchone()
                return row.get("total_value") or 0

        finally:
            connection.close()
            
    def discard_item(self, item, amount_fraction=None):
        name = item.get("name")

        if not name:
            return "Non ho capito quale prodotto hai buttato."

        quantity_value = self.clean_quantity(item.get("quantity"))

        def to_decimal(value):
            if value is None:
                return None
            if isinstance(value, Decimal):
                return value
            return Decimal(str(value))

        connection = self.get_connection()

        try:
            with connection.cursor() as cursor:
                sql = """
                SELECT *
                FROM items
                WHERE name LIKE %s
                AND (quantity IS NULL OR quantity > 0)
                ORDER BY expiry_date IS NULL, expiry_date ASC, id ASC
                LIMIT 1
                """
                cursor.execute(sql, (f"%{name}%",))
                row = cursor.fetchone()

                if not row:
                    return f"Non ho trovato {name} nella dispensa."

                item_id = row["id"]
                db_name = row["name"]
                unit = row.get("unit")
                current_quantity = to_decimal(row.get("quantity"))
                initial_quantity = to_decimal(row.get("initial_quantity"))
                price = to_decimal(row.get("price"))

                if amount_fraction is None:
                    amount_fraction = item.get("amount_fraction")

                if current_quantity is None:
                    wasted_quantity = None
                    new_quantity = Decimal("0")
                else:
                    if amount_fraction is not None:
                        wasted_quantity = current_quantity * Decimal(str(amount_fraction))
                    elif quantity_value is not None:
                        wasted_quantity = to_decimal(quantity_value)
                    else:
                        wasted_quantity = current_quantity

                    if wasted_quantity > current_quantity:
                        wasted_quantity = current_quantity

                    new_quantity = current_quantity - wasted_quantity

                    if new_quantity < Decimal("0.0001"):
                        new_quantity = Decimal("0")

                estimated_value = None

                if (
                    price is not None
                    and wasted_quantity is not None
                    and initial_quantity is not None
                    and initial_quantity > 0
                ):
                    estimated_value = price * (wasted_quantity / initial_quantity)

                sql = """
                INSERT INTO waste_log
                (item_id, name, quantity, unit, estimated_value, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    item_id,
                    db_name,
                    wasted_quantity,
                    unit,
                    estimated_value,
                    item.get("notes")
                ))

                sql = """
                UPDATE items
                SET quantity = %s
                WHERE id = %s
                """
                cursor.execute(sql, (new_quantity, item_id))

                connection.commit()

                value_text = ""
                if estimated_value is not None:
                    value_text = f" Valore buttato circa €{estimated_value:.2f}."

                return f"Ho registrato {db_name} come buttato.{value_text}"

        finally:
            connection.close()

            
    def list_waste_log(self):
        connection = self.get_connection()

        try:
            with connection.cursor() as cursor:
                sql = """
                SELECT name, quantity, unit, estimated_value, created_at
                FROM waste_log
                ORDER BY created_at DESC
                LIMIT 20
                """
                cursor.execute(sql)
                rows = cursor.fetchall()

                if not rows:
                    return "Non ho ancora registrato prodotti buttati."

                lines = ["🗑 Prodotti buttati:"]

                for row in rows:
                    name = row["name"]
                    quantity = row.get("quantity")
                    unit = row.get("unit") or ""
                    value = row.get("estimated_value")

                    text = f"• {name}"

                    if quantity is not None:
                        text += f" - {quantity:g} {unit}"

                    if value is not None:
                        text += f" - circa €{value:.2f}"

                    lines.append(text)

                return "\n".join(lines)

        finally:
            connection.close()
            
    def get_last_draft_receipt(self, chat_id):
        connection = self.get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM receipts
                    WHERE chat_id = %s
                    AND status = 'draft'
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (chat_id,),
                )
                return cursor.fetchone()
        finally:
            connection.close()


    def get_receipt_lines(self, receipt_id):
        connection = self.get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM receipt_lines
                    WHERE receipt_id = %s
                    ORDER BY id ASC
                    """,
                    (receipt_id,),
                )
                return cursor.fetchall()
        finally:
            connection.close()


    def cancel_receipt(self, receipt_id):
        connection = self.get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE receipts
                    SET status = 'cancelled',
                        cancelled_at = NOW()
                    WHERE id = %s
                    AND status = 'draft'
                    """,
                    (receipt_id,),
                )
                connection.commit()
                return cursor.rowcount
        finally:
            connection.close()


    def confirm_receipt(self, receipt_id):
        connection = self.get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE receipt_lines
                    SET added_to_pantry = TRUE
                    WHERE receipt_id = %s
                    """,
                    (receipt_id,),
                )

                cursor.execute(
                    """
                    UPDATE receipts
                    SET status = 'confirmed',
                        confirmed_at = NOW()
                    WHERE id = %s
                    AND status = 'draft'
                    """,
                    (receipt_id,),
                )

                connection.commit()
                return cursor.rowcount
        finally:
            connection.close()