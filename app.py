import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
from io import BytesIO
import pandas as pd

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="Safdar Garments POS",
    page_icon="👕",
    layout="wide"
)

DB_NAME = "safdar_garments.db"

# Login credentials requested by user
ADMIN_USERNAME = "safdar123"
ADMIN_PASSWORD = "009988"


# =========================================================
# DATABASE
# =========================================================

def get_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


conn = get_db()
cursor = conn.cursor()


def init_db():

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            size TEXT,
            color TEXT,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE,
            customer_name TEXT,
            customer_phone TEXT,
            customer_address TEXT,
            payment_method TEXT,
            payment_account TEXT,
            total REAL,
            seller TEXT,
            sale_date TEXT
        )
    """)

    cursor.execute("""
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


init_db()


# =========================================================
# 100 PRODUCTS
# =========================================================

def create_100_products():

    count = cursor.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    if count >= 100:
        return

    categories = [
        "Men Shirts",
        "Men T-Shirts",
        "Men Pants",
        "Men Shalwar Kameez",
        "Women Suits",
        "Women Dresses",
        "Kids Wear",
        "Jackets",
        "Hoodies",
        "Jeans"
    ]

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

    sizes = [
        "S",
        "M",
        "L",
        "XL",
        "XXL"
    ]

    products = []

    for i in range(1, 101):

        category = categories[(i - 1) % len(categories)]
        color = colors[(i - 1) % len(colors)]
        size = sizes[(i - 1) % len(sizes)]

        price = 1200 + ((i * 175) % 5000)
        stock = 10 + (i % 41)

        products.append(
            (
                f"Safdar {category} {i:03d}",
                category,
                size,
                color,
                price,
                stock
            )
        )

    cursor.executemany("""
        INSERT INTO products
        (name, category, size, color, price, stock)
        VALUES (?, ?, ?, ?, ?, ?)
    """, products)

    conn.commit()


create_100_products()


# =========================================================
# SESSION STATE
# =========================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "role" not in st.session_state:
    st.session_state.role = ""

if "cart" not in st.session_state:
    st.session_state.cart = []


# =========================================================
# LOGIN
# =========================================================

def login_page():

    st.title("👕 Safdar Garments POS")
    st.subheader("🔐 Secure Login")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:

        username = st.text_input(
            "Username",
            placeholder="Enter username"
        )

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter password"
        )

        role = st.selectbox(
            "Login As",
            ["Admin", "Seller"]
        )

        if st.button(
            "🔓 Login",
            use_container_width=True
        ):

            if (
                username == ADMIN_USERNAME
                and password == ADMIN_PASSWORD
            ):

                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = role.lower()

                st.success("Login successful!")
                st.rerun()

            else:

                st.error("Invalid username or password.")


# =========================================================
# LOGOUT
# =========================================================

def logout():

    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.cart = []

    st.rerun()


# =========================================================
# ADMIN DASHBOARD
# =========================================================

def admin_dashboard():

    st.title("👑 Admin Dashboard")

    st.sidebar.success(
        f"Logged in: {st.session_state.username}"
    )

    if st.sidebar.button("🚪 Logout"):
        logout()

    menu = st.sidebar.radio(
        "Admin Menu",
        [
            "Dashboard",
            "Products",
            "Stock Management",
            "Sales",
            "New POS Sale"
        ]
    )

    # -----------------------------------------------------
    # DASHBOARD
    # -----------------------------------------------------

    if menu == "Dashboard":

        total_products = cursor.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]

        total_stock = cursor.execute(
            "SELECT COALESCE(SUM(stock),0) FROM products"
        ).fetchone()[0]

        total_sales = cursor.execute(
            "SELECT COUNT(*) FROM sales"
        ).fetchone()[0]

        revenue = cursor.execute(
            "SELECT COALESCE(SUM(total),0) FROM sales"
        ).fetchone()[0]

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Products", total_products)
        c2.metric("Total Stock", total_stock)
        c3.metric("Invoices", total_sales)
        c4.metric("Revenue", f"Rs. {revenue:,.0f}")

        st.divider()

        st.subheader("📊 Recent Sales")

        df = pd.read_sql_query("""
            SELECT
                invoice_no AS Invoice,
                customer_name AS Customer,
                payment_method AS Payment,
                total AS Total,
                seller AS Seller,
                sale_date AS Date
            FROM sales
            ORDER BY id DESC
            LIMIT 20
        """, conn)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

    # -----------------------------------------------------
    # PRODUCTS
    # -----------------------------------------------------

    elif menu == "Products":

        st.subheader("👕 All Products")

        df = pd.read_sql_query(
            "SELECT * FROM products",
            conn
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

    # -----------------------------------------------------
    # STOCK
    # -----------------------------------------------------

    elif menu == "Stock Management":

        st.subheader("📦 Stock Management")

        products = pd.read_sql_query(
            "SELECT * FROM products",
            conn
        )

        product_name = st.selectbox(
            "Select Product",
            products["name"].tolist()
        )

        product = products[
            products["name"] == product_name
        ].iloc[0]

        st.write(
            f"Current Stock: **{product['stock']}**"
        )

        new_stock = st.number_input(
            "New Stock",
            min_value=0,
            value=int(product["stock"])
        )

        if st.button("💾 Update Stock"):

            cursor.execute("""
                UPDATE products
                SET stock = ?
                WHERE id = ?
            """, (new_stock, int(product["id"])))

            conn.commit()

            st.success("Stock updated successfully.")
            st.rerun()

    # -----------------------------------------------------
    # SALES
    # -----------------------------------------------------

    elif menu == "Sales":

        st.subheader("🧾 Sales Records")

        df = pd.read_sql_query("""
            SELECT
                invoice_no AS Invoice,
                customer_name AS Customer,
                customer_phone AS Phone,
                payment_method AS Payment,
                total AS Total,
                seller AS Seller,
                sale_date AS Date
            FROM sales
            ORDER BY id DESC
        """, conn)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        if not df.empty:

            csv = df.to_csv(index=False).encode(
                "utf-8"
            )

            st.download_button(
                "⬇️ Download Sales CSV",
                csv,
                "safdar_sales.csv",
                "text/csv"
            )

    # -----------------------------------------------------
    # POS
    # -----------------------------------------------------

    elif menu == "New POS Sale":

        pos_page()


# =========================================================
# SELLER DASHBOARD
# =========================================================

def seller_dashboard():

    st.title("🧑‍💼 Seller Dashboard")

    st.sidebar.success(
        f"Seller: {st.session_state.username}"
    )

    if st.sidebar.button("🚪 Logout"):
        logout()

    menu = st.sidebar.radio(
        "Seller Menu",
        [
            "POS",
            "My Sales"
        ]
    )

    if menu == "POS":

        pos_page()

    elif menu == "My Sales":

        df = pd.read_sql_query("""
            SELECT
                invoice_no AS Invoice,
                customer_name AS Customer,
                payment_method AS Payment,
                total AS Total,
                sale_date AS Date
            FROM sales
            WHERE seller = ?
            ORDER BY id DESC
        """, conn, params=(st.session_state.username,))

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# POS PAGE
# =========================================================

def pos_page():

    st.header("🛒 New POS Sale")

    products = pd.read_sql_query(
        "SELECT * FROM products WHERE stock > 0",
        conn
    )

    if products.empty:
        st.warning("No products available.")
        return

    # -----------------------------------------------------
    # CUSTOMER
    # -----------------------------------------------------

    st.subheader("👤 Customer Information")

    c1, c2 = st.columns(2)

    with c1:

        customer_name = st.text_input(
            "Customer Name *"
        )

        customer_phone = st.text_input(
            "Customer Phone *",
            max_chars=11,
            placeholder="03XXXXXXXXX"
        )

    with c2:

        customer_address = st.text_area(
            "Customer Address"
        )

    # -----------------------------------------------------
    # PRODUCT SELECTION
    # -----------------------------------------------------

    st.divider()
    st.subheader("👕 Add Products")

    product_names = products["name"].tolist()

    selected_product = st.selectbox(
        "Select Product",
        product_names
    )

    selected = products[
        products["name"] == selected_product
    ].iloc[0]

    p1, p2, p3, p4 = st.columns(4)

    p1.write(f"**Category:** {selected['category']}")
    p2.write(f"**Size:** {selected['size']}")
    p3.write(f"**Color:** {selected['color']}")
    p4.write(f"**Price:** Rs. {selected['price']:,.0f}")

    quantity = st.number_input(
        "Quantity",
        min_value=1,
        max_value=int(selected["stock"]),
        value=1
    )

    if st.button(
        "➕ Add To Cart",
        use_container_width=True
    ):

        found = False

        for item in st.session_state.cart:

            if item["id"] == int(selected["id"]):

                item["quantity"] += quantity
                found = True

        if not found:

            st.session_state.cart.append({
                "id": int(selected["id"]),
                "name": selected["name"],
                "price": float(selected["price"]),
                "quantity": quantity
            })

        st.success("Product added to cart.")

    # -----------------------------------------------------
    # CART
    # -----------------------------------------------------

    st.divider()

    st.subheader("🛍️ Cart")

    if not st.session_state.cart:

        st.info("Cart is empty.")

    else:

        total = 0

        for index, item in enumerate(
            st.session_state.cart
        ):

            subtotal = (
                item["price"] *
                item["quantity"]
            )

            total += subtotal

            c1, c2, c3, c4, c5 = st.columns(
                [3, 1, 1, 1, 1]
            )

            c1.write(item["name"])
            c2.write(f"Rs. {item['price']:,.0f}")
            c3.write(item["quantity"])
            c4.write(f"Rs. {subtotal:,.0f}")

            if c5.button(
                "❌",
                key=f"remove_{index}"
            ):

                st.session_state.cart.pop(index)
                st.rerun()

        st.markdown(
            f"## Total: Rs. {total:,.0f}"
        )

        # -------------------------------------------------
        # PAYMENT
        # -------------------------------------------------

        st.subheader("💳 Payment Method")

        payment_method = st.radio(
            "Select Payment",
            [
                "Cash",
                "JazzCash",
                "Easypaisa",
                "Credit Card"
            ],
            horizontal=True
        )

        payment_account = ""

        if payment_method in [
            "JazzCash",
            "Easypaisa"
        ]:

            payment_account = st.text_input(
                f"{payment_method} Mobile/Account Number *",
                max_chars=11,
                placeholder="03XXXXXXXXX"
            )

            if payment_account:

                if (
                    not payment_account.isdigit()
                    or len(payment_account) != 11
                    or not payment_account.startswith("03")
                ):

                    st.error(
                        "Please enter a valid 11-digit Pakistani mobile number."
                    )

        elif payment_method == "Credit Card":

            st.info(
                "For security, this POS does not store "
                "full card numbers or CVV."
            )

            card_last4 = st.text_input(
                "Last 4 digits of card",
                max_chars=4
            )

            if card_last4:
                if (
                    not card_last4.isdigit()
                    or len(card_last4) != 4
                ):
                    st.error(
                        "Enter exactly 4 digits."
                    )

            payment_account = (
                f"Card ending {card_last4}"
                if card_last4
                else ""
            )

        # -------------------------------------------------
        # COMPLETE SALE
        # -------------------------------------------------

        if st.button(
            "🧾 Generate Bill / Complete Sale",
            type="primary",
            use_container_width=True
        ):

            # Customer validation

            if not customer_name.strip():

                st.error(
                    "Customer name is required."
                )
                return

            if (
                not customer_phone.isdigit()
                or len(customer_phone) != 11
                or not customer_phone.startswith("03")
            ):

                st.error(
                    "Customer phone must be a valid 11-digit number."
                )
                return

            # Payment validation

            if payment_method in [
                "JazzCash",
                "Easypaisa"
            ]:

                if (
                    not payment_account.isdigit()
                    or len(payment_account) != 11
                    or not payment_account.startswith("03")
                ):

                    st.error(
                        "Enter valid 11-digit payment account number."
                    )
                    return

            # Invoice

            invoice_no = (
                "SG-"
                + datetime.now().strftime(
                    "%Y%m%d%H%M%S"
                )
            )

            sale_date = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            # Save sale

            cursor.execute("""
                INSERT INTO sales
                (
                    invoice_no,
                    customer_name,
                    customer_phone,
                    customer_address,
                    payment_method,
                    payment_account,
                    total,
                    seller,
                    sale_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice_no,
                customer_name,
                customer_phone,
                customer_address,
                payment_method,
                payment_account,
                total,
                st.session_state.username,
                sale_date
            ))

            sale_id = cursor.lastrowid

            # Save items + decrease stock

            for item in st.session_state.cart:

                cursor.execute("""
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
                """, (
                    sale_id,
                    item["id"],
                    item["name"],
                    item["quantity"],
                    item["price"],
                    item["price"] * item["quantity"]
                ))

                cursor.execute("""
                    UPDATE products
                    SET stock = stock - ?
                    WHERE id = ?
                    AND stock >= ?
                """, (
                    item["quantity"],
                    item["id"],
                    item["quantity"]
                ))

            conn.commit()

            # Create bill

            bill = create_bill(
                invoice_no,
                customer_name,
                customer_phone,
                customer_address,
                payment_method,
                total,
                sale_date,
                st.session_state.cart
            )

            st.session_state.cart = []

            st.success(
                f"Sale completed successfully! Invoice: {invoice_no}"
            )

            st.download
