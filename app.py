import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import io

# =========================================================
# SAFDAR GARMENTS - COMPLETE STREAMLIT POS
# =========================================================

st.set_page_config(
    page_title="Safdar Garments POS",
    page_icon="👕",
    layout="wide"
)

DB = "safdar_garments.db"

# ---------------- DATABASE ----------------

def get_db():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            size TEXT,
            color TEXT,
            price REAL,
            stock INTEGER
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

    # Create 100 products automatically
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


init_db()

# ---------------- SESSION ----------------

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "role" not in st.session_state:
    st.session_state.role = ""

if "cart" not in st.session_state:
    st.session_state.cart = []

if "last_bill" not in st.session_state:
    st.session_state.last_bill = ""

# ---------------- FUNCTIONS ----------------

def get_products():
    conn = get_db()
    df = pd.read_sql_query(
        "SELECT * FROM products ORDER BY id",
        conn
    )
    conn.close()
    return df


def get_sales():
    conn = get_db()
    df = pd.read_sql_query(
        "SELECT * FROM sales ORDER BY id DESC",
        conn
    )
    conn.close()
    return df


def add_to_cart(product_id, quantity):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, name, price, stock FROM products WHERE id=?",
        (product_id,)
    )

    product = cur.fetchone()
    conn.close()

    if not product:
        return False, "Product not found."

    pid, name, price, stock = product

    if quantity <= 0:
        return False, "Quantity must be greater than 0."

    existing_qty = 0

    for item in st.session_state.cart:
        if item["product_id"] == pid:
            existing_qty = item["quantity"]

    if existing_qty + quantity > stock:
        return False, f"Only {stock} items available."

    found = False

    for item in st.session_state.cart:
        if item["product_id"] == pid:
            item["quantity"] += quantity
            item["subtotal"] = item["quantity"] * item["price"]
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

    return True, "Product added."


def cart_total():
    return sum(
        item["subtotal"]
        for item in st.session_state.cart
    )


def create_sale(
    customer,
    phone,
    address,
    payment,
    payment_number,
    seller
):

    if len(st.session_state.cart) == 0:
        return None, "Cart is empty."

    total = cart_total()

    invoice = "SG-" + datetime.now().strftime("%Y%m%d%H%M%S")

    date = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    conn = get_db()
    cur = conn.cursor()

    # Check stock again
    for item in st.session_state.cart:

        cur.execute(
            "SELECT stock FROM products WHERE id=?",
            (item["product_id"],)
        )

        row = cur.fetchone()

        if not row:
            conn.close()
            return None, "Product not found."

        if row[0] < item["quantity"]:
            conn.close()
            return None, (
                f"Not enough stock for {item['name']}."
            )

    # Sale
    cur.execute("""
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
    """, (
        invoice,
        customer,
        phone,
        address,
        payment,
        payment_number,
        total,
        seller,
        date
    ))

    sale_id = cur.lastrowid

    # Items + stock update
    for item in st.session_state.cart:

        cur.execute("""
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
            item["product_id"],
            item["name"],
            item["quantity"],
            item["price"],
            item["subtotal"]
        ))

        cur.execute("""
            UPDATE products
            SET stock = stock - ?
            WHERE id = ?
        """, (
            item["quantity"],
            item["product_id"]
        ))

    conn.commit()
    conn.close()

    # Create bill
    bill = ""
    bill += "================================\n"
    bill += "       SAFDAR GARMENTS\n"
    bill += "          SALES INVOICE\n"
    bill += "================================\n"
    bill += f"Invoice: {invoice}\n"
    bill += f"Date: {date}\n"
    bill += f"Seller: {seller}\n"
    bill += "--------------------------------\n"
    bill += f"Customer: {customer}\n"
    bill += f"Phone: {phone}\n"
    bill += f"Address: {address}\n"
    bill += "--------------------------------\n"

    for item in st.session_state.cart:
        bill += (
            f"{item['name']}\n"
            f"  {item['quantity']} x "
            f"Rs.{item['price']:.0f} = "
            f"Rs.{item['subtotal']:.0f}\n"
        )

    bill += "--------------------------------\n"
    bill += f"Payment: {payment}\n"

    if payment_number:
        bill += f"Payment Ref: {payment_number}\n"

    bill += f"TOTAL: Rs.{total:.0f}\n"
    bill += "================================\n"
    bill += "       Thank You!\n"
    bill += "================================\n"

    return bill, None


# ---------------- LOGIN ----------------

def login_page():

    st.title("👕 Safdar Garments")
    st.subheader("Point of Sale System")

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:

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
            "🔐 Login",
            use_container_width=True
        ):

            if (
                username == "safdar123"
                and password == "009988"
            ):

                st.session_state.logged_in = True
                st.session_state.role = role

                st.rerun()

            else:
                st.error(
                    "Wrong username or password."
                )

        st.info(
            "Demo Login: safdar123 / 009988"
        )


# ---------------- POS ----------------

def pos_page():

    st.header("🧾 New Sale")

    products = get_products()

    if products.empty:
        st.warning("No products available.")
        return

    # Customer
    st.subheader("Customer Information")

    c1, c2 = st.columns(2)

    with c1:
        customer = st.text_input(
            "Customer Name",
            key="customer_name"
        )

        phone = st.text_input(
            "Customer Phone",
            key="customer_phone"
        )

    with c2:
        address = st.text_input(
            "Customer Address",
            key="customer_address"
        )

    st.divider()

    # Product
    st.subheader("Add Product")

    product_options = {}

    for _, row in products.iterrows():
        label = (
            f"{row['id']} - "
            f"{row['name']} | "
            f"{row['category']} | "
            f"{row['size']} | "
            f"{row['color']} | "
            f"Rs.{row['price']:.0f} | "
            f"Stock: {row['stock']}"
        )

        product_options[label] = int(row["id"])

    selected_label = st.selectbox(
        "Select Product",
        list(product_options.keys())
    )

    selected_id = product_options[selected_label]

    selected_product = products[
        products["id"] == selected_id
    ].iloc[0]

    q1, q2 = st.columns(2)

    with q1:
        quantity = st.number_input(
            "Quantity",
            min_value=1,
            max_value=int(selected_product["stock"])
            if selected_product["stock"] > 0
            else 1,
            value=1
        )

    with q2:
        st.write("")
        st.write("")
        if st.button(
            "➕ Add to Cart",
            use_container_width=True
        ):

            if selected_product["stock"] <= 0:
                st.error("Out of stock.")
            else:
                ok, msg = add_to_cart(
                    selected_id,
                    quantity
                )

                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # Cart
    st.divider()
    st.subheader("🛒 Cart")

    if st.session_state.cart:

        cart_df = pd.DataFrame(
            st.session_state.cart
        )

        display_df = cart_df[
            [
                "name",
                "price",
                "quantity",
                "subtotal"
            ]
        ].copy()

        display_df.columns = [
            "Product",
            "Price",
            "Qty",
            "Subtotal"
        ]

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        st.metric(
            "Grand Total",
            f"Rs. {cart_total():,.0f}"
        )

        if st.button(
            "🗑️ Clear Cart",
            use_container_width=True
        ):
            st.session_state.cart = []
            st.rerun()

    else:

        st.info("Cart is empty.")

    # Payment
    if st.session_state.cart:

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

        if payment in [
            "JazzCash",
            "Easypaisa"
        ]:

            payment_number = st.text_input(
                "11-Digit Mobile Number",
                placeholder="03XXXXXXXXX"
            )

            if payment_number:
                if (
                    len(payment_number) != 11
                    or not payment_number.isdigit()
                    or not payment_number.startswith("03")
                ):
                    st.warning(
                        "Enter valid 11-digit number "
                        "starting with 03."
                    )

        elif payment == "Credit Card":

            payment_number = st.text_input(
                "Last 4 Digits of Card",
                max_chars=4,
                placeholder="1234"
            )

            st.caption(
                "For security, full card number "
                "and CVV are not stored."
            )

        st.divider()

        seller = (
            "Admin"
            if st.session_state.role == "Admin"
            else "Seller"
        )

        if st.button(
            "✅ COMPLETE SALE",
            use_container_width=True,
            type="primary"
        ):

            # Customer validation
            if not customer.strip():
                st.error(
                    "Please enter customer name."
                )
                return

            # Payment validation
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
                        "Enter valid 11-digit mobile number."
                    )
                    return

            if payment == "Credit Card":

                if (
                    len(payment_number) != 4
                    or not payment_number.isdigit()
                ):
                    st.error(
                        "Enter valid last 4 digits."
                    )
                    return

            bill, error = create_sale(
                customer,
                phone,
                address,
                payment,
                payment_number,
                seller
            )

            if error:
                st.error(error)
                return

            st.session_state.last_bill = bill
            st.session_state.cart = []

            st.success(
                "Sale completed successfully!"
            )

            st.download_button(
                "⬇️ Download Bill",
                data=bill,
                file_name=(
                    f"{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    "_bill.txt"
                ),
                mime="text/plain",
                use_container_width=True
            )


# ---------------- ADMIN DASHBOARD ----------------

def admin_dashboard():

    st.header("👑 Admin Dashboard")

    products = get_products()
    sales = get_sales()

    total_products = len(products)

    total_stock = (
        int(products["stock"].sum())
        if not products.empty
        else 0
    )

    total_sales = len(sales)

    revenue = (
        float(sales["total"].sum())
        if not sales.empty
        else 0
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Products",
            total_products
        )

    with c2:
        st.metric(
            "Total Stock",
            total_stock
        )

    with c3:
        st.metric(
            "Invoices",
            total_sales
        )

    with c4:
        st.metric(
            "Revenue",
            f"Rs. {revenue:,.0f}"
        )

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "🧾 POS",
            "📦 Products",
            "📊 Sales",
            "⚙️ Stock Management"
        ]
    )

    with tab1:
        pos_page()

    with tab2:

        st.subheader("All Products")

        st.dataframe(
            products,
            use_container_width=True,
            hide_index=True
        )

        csv = products.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "⬇️ Download Products CSV",
            csv,
            "products.csv",
            "text/csv"
        )

    with tab3:

        st.subheader("Sales Records")

        if sales.empty:
            st.info("No sales yet.")

        else:

            st.dataframe(
                sales,
                use_container_width=True,
                hide_index=True
            )

            csv = sales.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                "⬇️ Download Sales CSV",
                csv,
                "sales.csv",
                "text/csv"
            )

    with tab4:

        st.subheader("Update Product Stock")

        product_map = {}

        for _, row in products.iterrows():
            product_map[
                f"{row['id']} - {row['name']}"
            ] = int(row["id"])

        selected = st.selectbox(
            "Select Product",
            list(product_map.keys())
        )

        pid = product_map[selected]

        current_stock = int(
            products[
                products["id"] == pid
            ].iloc[0]["stock"]
        )

        st.write(
            f"Current Stock: **{current_stock}**"
        )

        new_stock = st.number_input(
            "New Stock",
            min_value=0,
            value=current_stock
        )

        if st.button(
            "💾 Update Stock",
            use_container_width=True
        ):

            conn = get_db()
            cur = conn.cursor()

            cur.execute(
                """
                UPDATE products
                SET stock=?
                WHERE id=?
                """,
                (new_stock, pid)
            )

            conn.commit()
            conn.close()

            st.success(
                "Stock updated successfully."
            )

            st.rerun()


# ---------------- SELLER DASHBOARD ----------------

def seller_dashboard():

    st.header("🧑‍💼 Seller Dashboard")

    tab1, tab2 = st.tabs(
        [
            "🧾 New Sale",
            "📊 My Sales"
        ]
    )

    with tab1:
        pos_page()

    with tab2:

        sales = get_sales()

        if sales.empty:
            st.info("No sales yet.")

        else:

            st.dataframe(
                sales,
                use_container_width=True,
                hide_index=True
            )

            total = sales["total"].sum()

            st.metric(
                "Total Sales",
                f"Rs. {total:,.0f}"
            )


# ---------------- MAIN APP ----------------

if not st.session_state.logged_in:

    login_page()

else:

    # Sidebar
    st.sidebar.title("👕 Safdar Garments")

    st.sidebar.write(
        f"Logged in as: **{st.session_state.role}**"
    )

    st.sidebar.divider()

    if st.sidebar.button(
        "🚪 Logout",
        use_container_width=True
    ):

        st.session_state.logged_in = False
        st.session_state.role = ""
        st.session_state.cart
