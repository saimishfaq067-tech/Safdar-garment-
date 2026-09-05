import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

# =========================================================
# SAFDAR GARMENTS POS - SINGLE FILE APP
# =========================================================

st.set_page_config(
    page_title="Safdar Garments POS",
    page_icon="👕",
    layout="wide"
)

DB = "safdar_garments.db"

# =========================================================
# DATABASE
# =========================================================

def db():
    return sqlite3.connect(DB, check_same_thread=False)


def setup_database():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            size TEXT NOT NULL,
            color TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice TEXT,
            customer TEXT,
            phone TEXT,
            address TEXT,
            payment TEXT,
            payment_number TEXT,
            total REAL,
            seller TEXT,
            date TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER,
            product_id INTEGER,
            product_name TEXT,
            quantity INTEGER,
            price REAL,
            subtotal REAL
        )
    """)

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM products")
    count = cur.fetchone()[0]

    if count == 0:

        categories = [
            "Men Shirt",
            "Men T-Shirt",
            "Men Pant",
            "Shalwar Kameez",
            "Ladies Suit",
            "Ladies Dress",
            "Kids Wear",
            "Jacket",
            "Hoodie",
            "Jeans"
        ]

        sizes = ["S", "M", "L", "XL", "XXL"]

        colors = [
            "Black",
            "White",
            "Blue",
            "Navy",
            "Grey",
            "Red",
            "Green",
            "Brown",
            "Cream",
            "Maroon"
        ]

        for i in range(1, 101):

            category = categories[(i - 1) % len(categories)]
            size = sizes[(i - 1) % len(sizes)]
            color = colors[(i - 1) % len(colors)]

            price = 1000 + ((i * 250) % 5000)
            stock = 20 + (i % 30)

            name = f"{category} {i}"

            cur.execute("""
                INSERT INTO products
                (name, category, size, color, price, stock)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                name,
                category,
                size,
                color,
                price,
                stock
            ))

        conn.commit()

    conn.close()


setup_database()

# =========================================================
# SESSION
# =========================================================

if "login" not in st.session_state:
    st.session_state.login = False

if "role" not in st.session_state:
    st.session_state.role = ""

if "cart" not in st.session_state:
    st.session_state.cart = []

if "bill" not in st.session_state:
    st.session_state.bill = ""

# =========================================================
# DATA FUNCTIONS
# =========================================================

def products_data():

    conn = db()

    df = pd.read_sql_query(
        "SELECT * FROM products ORDER BY id",
        conn
    )

    conn.close()

    return df


def sales_data():

    conn = db()

    df = pd.read_sql_query(
        "SELECT * FROM sales ORDER BY id DESC",
        conn
    )

    conn.close()

    return df


def total_cart():

    return sum(
        item["subtotal"]
        for item in st.session_state.cart
    )


# =========================================================
# LOGIN
# =========================================================

def login_page():

    st.title("👕 SAFDAR GARMENTS")
    st.subheader("Point of Sale System")

    st.divider()

    left, center, right = st.columns(
        [1, 2, 1]
    )

    with center:

        st.markdown("### 🔐 Login")

        username = st.text_input(
            "Username"
        )

        password = st.text_input(
            "Password",
            type="password"
        )

        role = st.selectbox(
            "Login As",
            [
                "Admin",
                "Seller"
            ]
        )

        if st.button(
            "LOGIN",
            use_container_width=True,
            type="primary"
        ):

            if (
                username == "safdar123"
                and password == "009988"
            ):

                st.session_state.login = True
                st.session_state.role = role

                st.rerun()

            else:

                st.error(
                    "❌ Wrong username or password"
                )

        st.info(
            "Username: safdar123\n\n"
            "Password: 009988"
        )


# =========================================================
# ADD PRODUCT TO CART
# =========================================================

def add_cart(product_id, quantity):

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, price, stock
        FROM products
        WHERE id=?
    """, (product_id,))

    product = cur.fetchone()

    conn.close()

    if not product:
        return False, "Product not found."

    pid, name, price, stock = product

    if stock <= 0:
        return False, "Product is out of stock."

    current_qty = 0

    for item in st.session_state.cart:

        if item["product_id"] == pid:
            current_qty = item["quantity"]

    if current_qty + quantity > stock:

        return False, (
            f"Only {stock} pieces available."
        )

    found = False

    for item in st.session_state.cart:

        if item["product_id"] == pid:

            item["quantity"] += quantity

            item["subtotal"] = (
                item["quantity"] *
                item["price"]
            )

            found = True

            break

    if not found:

        st.session_state.cart.append({
            "product_id": pid,
            "name": name,
            "price": price,
            "quantity": quantity,
            "subtotal": price * quantity
        })

    return True, "Product added to cart."


# =========================================================
# POS / BILLING
# =========================================================

def pos_page():

    st.header("🧾 New Sale / Billing")

    products = products_data()

    if products.empty:

        st.warning(
            "No products available."
        )

        return

    # -----------------------------------------------------
    # CUSTOMER
    # -----------------------------------------------------

    st.subheader("👤 Customer Information")

    c1, c2 = st.columns(2)

    with c1:

        customer = st.text_input(
            "Customer Name"
        )

        phone = st.text_input(
            "Customer Phone"
        )

    with c2:

        address = st.text_input(
            "Customer Address"
        )

    st.divider()

    # -----------------------------------------------------
    # PRODUCT
    # -----------------------------------------------------

    st.subheader("📦 Select Product")

    product_list = []

    product_ids = {}

    for _, row in products.iterrows():

        text = (
            f"{row['id']} | "
            f"{row['name']} | "
            f"{row['size']} | "
            f"{row['color']} | "
            f"Rs.{row['price']:.0f} | "
            f"Stock: {row['stock']}"
        )

        product_list.append(text)

        product_ids[text] = int(row["id"])

    selected = st.selectbox(
        "Product",
        product_list
    )

    product_id = product_ids[selected]

    selected_product = products[
        products["id"] == product_id
    ].iloc[0]

    col1, col2, col3 = st.columns(3)

    with col1:

        st.write(
            "**Category:**",
            selected_product["category"]
        )

    with col2:

        st.write(
            "**Size:**",
            selected_product["size"]
        )

    with col3:

        st.write(
            "**Price:**",
            f"Rs.{selected_product['price']:.0f}"
        )

    quantity = st.number_input(
        "Quantity",
        min_value=1,
        max_value=max(
            1,
            int(selected_product["stock"])
        ),
        value=1
    )

    if st.button(
        "➕ ADD TO CART",
        use_container_width=True
    ):

        if selected_product["stock"] <= 0:

            st.error(
                "Product is out of stock."
            )

        else:

            ok, message = add_cart(
                product_id,
                quantity
            )

            if ok:

                st.success(message)

                st.rerun()

            else:

                st.error(message)

    # -----------------------------------------------------
    # CART
    # -----------------------------------------------------

    st.divider()

    st.subheader("🛒 Shopping Cart")

    if len(st.session_state.cart) == 0:

        st.info(
            "Cart is empty."
        )

    else:

        for index, item in enumerate(
            st.session_state.cart
        ):

            col1, col2, col3, col4, col5 = st.columns(
                [3, 1, 1, 1, 1]
            )

            with col1:
                st.write(
                    f"**{item['name']}**"
                )

            with col2:
                st.write(
                    f"Rs.{item['price']:.0f}"
                )

            with col3:
                st.write(
                    f"Qty: {item['quantity']}"
                )

            with col4:
                st.write(
                    f"Rs.{item['subtotal']:.0f}"
                )

            with col5:

                if st.button(
                    "❌",
                    key=f"remove_{index}"
                ):

                    st.session_state.cart.pop(
                        index
                    )

                    st.rerun()

        st.divider()

        st.metric(
            "TOTAL",
            f"Rs.{total_cart():,.0f}"
        )

        if st.button(
            "🗑️ CLEAR CART",
            use_container_width=True
        ):

            st.session_state.cart = []

            st.rerun()

    # -----------------------------------------------------
    # PAYMENT
    # -----------------------------------------------------

    if len(st.session_state.cart) > 0:

        st.divider()

        st.subheader("💳 Payment")

        payment = st.selectbox(
            "Payment Method",
            [
                "Cash",
                "JazzCash",
                "Easypaisa",
                "Credit Card"
            ]
        )

        payment_number = ""

        if payment == "JazzCash":

            payment_number = st.text_input(
                "JazzCash Number",
                placeholder="03XXXXXXXXX",
                max_chars=11
            )

            st.caption(
                "Enter 11 digit JazzCash number."
            )

        elif payment == "Easypaisa":

            payment_number = st.text_input(
                "Easypaisa Number",
                placeholder="03XXXXXXXXX",
                max_chars=11
            )

            st.caption(
                "Enter 11 digit Easypaisa number."
            )

        elif payment == "Credit Card":

            payment_number = st.text_input(
                "Last 4 Digits",
                placeholder="1234",
                max_chars=4
            )

            st.caption(
                "Only last 4 digits are used."
            )

        # -------------------------------------------------
        # COMPLETE SALE
        # -------------------------------------------------

        if st.button(
            "✅ COMPLETE SALE",
            use_container_width=True,
            type="primary"
        ):

            # Customer check

            if not customer.strip():

                st.error(
                    "Please enter customer name."
                )

                return

            # Payment check

            if payment in [
                "JazzCash",
                "Easypaisa"
            ]:

                if (
                    len(payment_number) != 11
                    or not payment_number.isdigit()
                    or not payment_number.startswith("03")
                ):

                    st.error(
                        "Please enter valid 11 digit mobile number."
                    )

                    return

            if payment == "Credit Card":

                if (
                    len(payment_number) != 4
                    or not payment_number.isdigit()
                ):

                    st.error(
                        "Please enter last 4 digits."
                    )

                    return

            # -------------------------------------------------
            # SAVE SALE
            # -------------------------------------------------

            conn = db()
            cur = conn.cursor()

            invoice = (
                "SG-"
                + datetime.now().strftime(
                    "%Y%m%d%H%M%S"
                )
            )

            date = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            total = total_cart()

            seller = st.session_state.role

            # Check stock

            for item in st.session_state.cart:

                cur.execute(
                    """
                    SELECT stock
                    FROM products
                    WHERE id=?
                    """,
                    (item["product_id"],)
                )

                stock = cur.fetchone()[0]

                if stock < item["quantity"]:

                    conn.close()

                    st.error(
                        f"Not enough stock for {item['name']}"
                    )

                    return

            # Sale insert

            cur.execute(
                """
                INSERT INTO sales
                (
                    invoice,
                    customer,
                    phone,
                    address,
                    payment,
                    payment_number,
                    total,
                    seller,
                    date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice,
                    customer,
                    phone,
                    address,
                    payment,
                    payment_number,
                    total,
                    seller,
                    date
                )
            )

            sale_id = cur.lastrowid

            # Items

            for item in st.session_state.cart:

                cur.execute(
                    """
                    INSERT INTO sale_items
                    (
                        sale_id,
                        product_id,
                        product_name,
                        quantity,
                        price,
                        subtotal
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sale_id,
                        item["product_id"],
                        item["name"],
                        item["quantity"],
                        item["price"],
                        item["subtotal"]
                    )
                )

                # Stock decrease

                cur.execute(
                    """
                    UPDATE products
                    SET stock = stock - ?
                    WHERE id=?
                    """,
                    (
                        item["quantity"],
                        item["product_id"]
                    )
                )

            conn.commit()
            conn.close()

            # -------------------------------------------------
            # BILL
            # -------------------------------------------------

            bill = ""

            bill += "====================================\n"
            bill += "          SAFDAR GARMENTS\n"
            bill += "             INVOICE\n"
            bill += "====================================\n"
            bill += f"Invoice: {invoice}\n"
            bill += f"Date: {date}\n"
            bill += f"Seller: {seller}\n"
            bill += "------------------------------------\n"
            bill += f"Customer: {customer}\n"
            bill += f"Phone: {phone}\n"
            bill += f"Address: {address}\n"
            bill += "------------------------------------\n"

            for item in st.session_state.cart:

                bill += (
                    f"{item['name']}\n"
                    f"{item['quantity']} x "
                    f"Rs.{item['price']:.0f}"
                    f" = Rs.{item['subtotal']:.0f}\n"
                )

            bill += "------------------------------------\n"
            bill += f"Payment: {payment}\n"

            if payment_number:

                bill += (
                    f"Payment Number/Ref: "
                    f"{payment_number}\n"
                )

            bill += "------------------------------------\n"
            bill += f"TOTAL: Rs.{total:.0f}\n"
            bill += "====================================\n"
            bill += "             THANK YOU!\n"
            bill += "        SAFDAR GARMENTS\n"
            bill += "====================================\n"

            st.session_state.bill = bill

            st.session_state.cart = []

            st.success(
                f"✅ Sale Completed! Invoice: {invoice}"
            )

    # -----------------------------------------------------
    # DOWNLOAD BILL
    # -----------------------------------------------------

    if st.session_state.bill:

        st.divider()

        st.subheader("🧾 Latest Bill")

        st.text(
            st.session_state.bill
        )

        st.download_button(
            "⬇️ DOWNLOAD BILL",
            data=st.session_state.bill,
            file_name="safdar_invoice.txt",
            mime="text/plain",
            use_container_width=True
        )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

def admin_dashboard():

    st.header("👑 ADMIN DASHBOARD")

    products = products_data()
    sales = sales_data()

    product_count = len(products)

    stock_count = (
        int(products["stock"].sum())
        if not products.empty
        else 0
    )

    invoice_count = len(sales)

    revenue = (
        float(sales["total"].sum())
        if not sales.empty
        else 0
    )

    # -----------------------------------------------------
    # METRICS
    # -----------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.metric(
            "📦 Products",
            product_count
        )

    with c2:

        st.metric(
            "📊 Stock",
            stock_count
        )

    with c3:

        st.metric(
            "🧾 Invoices",
            invoice_count
        )

    with c4:

        st.metric(
            "💰 Revenue",
            f"Rs.{revenue:,.0f}"
        )

    st.divider()

    # ----------------------------------
