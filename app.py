import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

# =====================================================
# SAFDAR GARMENTS POS
# =====================================================

st.set_page_config(
    page_title="Safdar Garments POS",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_FILE = "safdar_garments_pos.db"


# =====================================================
# DATABASE
# =====================================================

def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def init_db():

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            size TEXT NOT NULL,
            color TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT NOT NULL,
            customer TEXT,
            subtotal REAL NOT NULL,
            discount REAL NOT NULL,
            total REAL NOT NULL,
            payment TEXT NOT NULL,
            sale_date TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            total REAL NOT NULL
        )
    """)

    conn.commit()

    # 100 products automatically add honge
    count = cur.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    if count == 0:

        categories = [
            "Shalwar Kameez",
            "Kurta",
            "Pant",
            "Shirt",
            "T-Shirt",
            "Jeans",
            "Waistcoat",
            "Jacket",
            "Kids Wear",
            "Ladies Wear"
        ]

        sizes = [
            "S",
            "M",
            "L",
            "XL",
            "XXL"
        ]

        colors = [
            "Black",
            "White",
            "Blue",
            "Navy",
            "Grey",
            "Brown",
            "Green",
            "Maroon",
            "Cream",
            "Beige"
        ]

        products = []

        for i in range(1, 101):

            category = categories[(i - 1) % len(categories)]
            size = sizes[(i - 1) % len(sizes)]
            color = colors[(i - 1) % len(colors)]

            if category == "Shalwar Kameez":
                name = f"Safdar Shalwar Kameez {i:03d}"
                price = 3500 + ((i % 8) * 250)

            elif category == "Kurta":
                name = f"Safdar Kurta {i:03d}"
                price = 2200 + ((i % 7) * 200)

            elif category == "Pant":
                name = f"Safdar Pant {i:03d}"
                price = 1800 + ((i % 6) * 200)

            elif category == "Shirt":
                name = f"Safdar Shirt {i:03d}"
                price = 2000 + ((i % 7) * 200)

            elif category == "T-Shirt":
                name = f"Safdar T-Shirt {i:03d}"
                price = 1200 + ((i % 6) * 150)

            elif category == "Jeans":
                name = f"Safdar Jeans {i:03d}"
                price = 2800 + ((i % 6) * 250)

            elif category == "Waistcoat":
                name = f"Safdar Waistcoat {i:03d}"
                price = 3000 + ((i % 7) * 300)

            elif category == "Jacket":
                name = f"Safdar Jacket {i:03d}"
                price = 4500 + ((i % 7) * 400)

            elif category == "Kids Wear":
                name = f"Safdar Kids Wear {i:03d}"
                price = 1000 + ((i % 6) * 150)

            else:
                name = f"Safdar Ladies Wear {i:03d}"
                price = 2500 + ((i % 7) * 250)

            stock = 10 + (i % 21)

            products.append(
                (
                    name,
                    category,
                    size,
                    color,
                    price,
                    stock
                )
            )

        cur.executemany("""
            INSERT INTO products
            (name, category, size, color, price, stock)
            VALUES (?, ?, ?, ?, ?, ?)
        """, products)

        conn.commit()

    conn.close()


init_db()


# =====================================================
# SESSION STATE
# =====================================================

if "cart" not in st.session_state:
    st.session_state.cart = {}

if "last_invoice" not in st.session_state:
    st.session_state.last_invoice = None


# =====================================================
# FUNCTIONS
# =====================================================

def get_categories():

    conn = get_conn()

    rows = conn.execute(
        "SELECT DISTINCT category FROM products ORDER BY category"
    ).fetchall()

    conn.close()

    return ["All"] + [row[0] for row in rows]


def get_products(search="", category="All"):

    conn = get_conn()

    query = """
        SELECT
            id,
            name,
            category,
            size,
            color,
            price,
            stock
        FROM products
        WHERE 1=1
    """

    params = []

    if search:

        query += """
            AND (
                name LIKE ?
                OR category LIKE ?
                OR size LIKE ?
                OR color LIKE ?
            )
        """

        text = f"%{search}%"

        params.extend([
            text,
            text,
            text,
            text
        ])

    if category != "All":

        query += """
            AND category = ?
        """

        params.append(category)

    query += " ORDER BY id"

    df = pd.read_sql_query(
        query,
        conn,
        params=params
    )

    conn.close()

    return df


def make_invoice():

    return (
        "SG-" +
        datetime.now().strftime(
            "%Y%m%d%H%M%S%f"
        )[:17]
    )


def clear_cart():

    st.session_state.cart = {}


def add_to_cart(product_id, quantity):

    conn = get_conn()

    product = conn.execute("""
        SELECT
            id,
            name,
            price,
            stock
        FROM products
        WHERE id = ?
    """, (product_id,)).fetchone()

    conn.close()

    if not product:

        st.error("Product not found.")
        return

    pid, name, price, stock = product

    if stock <= 0:

        st.warning("Product out of stock.")
        return

    old_qty = (
        st.session_state.cart
        .get(pid, {})
        .get("quantity", 0)
    )

    new_qty = old_qty + quantity

    if new_qty > stock:

        st.warning(
            f"Only {stock} pieces available."
        )

        return

    st.session_state.cart[pid] = {
        "name": name,
        "price": float(price),
        "quantity": new_qty
    }


def cart_dataframe():

    rows = []

    for pid, item in st.session_state.cart.items():

        rows.append({
            "Product ID": pid,
            "Product": item["name"],
            "Price": item["price"],
            "Qty": item["quantity"],
            "Total": (
                item["price"] *
                item["quantity"]
            )
        })

    return pd.DataFrame(rows)


def save_sale(
    customer,
    discount,
    payment
):

    if not st.session_state.cart:
        return None

    conn = get_conn()
    cur = conn.cursor()

    invoice = make_invoice()

    subtotal = sum(
        item["price"] * item["quantity"]
        for item in st.session_state.cart.values()
    )

    discount = max(
        0.0,
        float(discount)
    )

    if discount > subtotal:
        discount = subtotal

    total = subtotal - discount

    sale_date = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # Stock check
    for pid, item in st.session_state.cart.items():

        stock = cur.execute(
            "SELECT stock FROM products WHERE id = ?",
            (pid,)
        ).fetchone()

        if (
            not stock
            or stock[0] < item["quantity"]
        ):

            conn.rollback()
            conn.close()

            st.error(
                f"Not enough stock for {item['name']}"
            )

            return None

    # Save sale
    cur.execute("""
        INSERT INTO sales
        (
            invoice_no,
            customer,
            subtotal,
            discount,
            total,
            payment,
            sale_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        invoice,
        customer.strip() or "Walk-in Customer",
        subtotal,
        discount,
        total,
        payment,
        sale_date
    ))

    # Save items + update stock
    for pid, item in st.session_state.cart.items():

        item_total = (
            item["price"] *
            item["quantity"]
        )

        cur.execute("""
            INSERT INTO sale_items
            (
                invoice_no,
                product_id,
                product_name,
                quantity,
                price,
                total
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            invoice,
            pid,
            item["name"],
            item["quantity"],
            item["price"],
            item_total
        ))

        cur.execute("""
            UPDATE products
            SET stock = stock - ?
            WHERE id = ?
        """, (
            item["quantity"],
            pid
        ))

    conn.commit()
    conn.close()

    return {
        "invoice": invoice,
        "customer": customer,
        "subtotal": subtotal,
        "discount": discount,
        "total": total,
        "payment": payment,
        "date": sale_date
    }


# =====================================================
# CSS
# =====================================================

st.markdown("""
<style>

.main-title {
    font-size: 34px;
    font-weight: 800;
}

.sub-title {
    color: #666;
    margin-bottom: 20px;
}

</style>
""", unsafe_allow_html=True)


# =====================================================
# HEADER
# =====================================================

st.markdown(
    '<div class="main-title">👕 SAFDAR GARMENTS</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub-title">'
    'Complete Garments Point of Sale System'
    '</div>',
    unsafe_allow_html=True
)

st.divider()


# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.title("📋 POS MENU")

page = st.sidebar.radio(
    "Select Page",
    [
        "🛒 New Sale",
        "📦 Inventory",
        "📊 Dashboard",
        "🧾 Sales History"
    ]
)

st.sidebar.divider()

st.sidebar.info(
    "Safdar Garments POS\n\n"
    "100 products automatically available."
)

if st.sidebar.button(
    "🗑️ Clear Current Cart",
    use_container_width=True
):

    clear_cart()
    st.rerun()


# =====================================================
# NEW SALE
# =====================================================

if page == "🛒 New Sale":

    st.header("🛒 New Sale")

    left, right = st.columns(
        [1.45, 1]
    )

    # -------------------------
    # PRODUCTS
    # -------------------------

    with left:

        st.subheader("Products")

        search = st.text_input(
            "🔎 Search Product",
            placeholder=(
                "Name, category, size or color"
            )
        )

        categories = get_categories()

        category = st.selectbox(
            "Category",
            categories
        )

        products = get_products(
            search,
            category
        )

        if products.empty:

            st.warning(
                "No products found."
            )

        else:

            st.caption(
                f"{len(products)} product(s) found"
            )

            for _, product in products.iterrows():

                with st.container(border=True):

                    c1, c2, c3 = st.columns(
                        [3, 1.3, 1]
                    )

                    with c1:

                        st.write(
                            f"**{product['name']}**"
                        )

                        st.caption(
                            f"Category: "
                            f"{product['category']} | "
                            f"Size: {product['size']} | "
                            f"Color: {product['color']}"
                        )

                    with c2:

                        st.write(
                            f"**Rs. "
                            f"{product['price']:,.0f}**"
                        )

                        st.caption(
                            f"Stock: {product['stock']}"
                        )

                    with c3:

                        qty = st.number_input(
                            "Qty",
                            min_value=1,
                            max_value=max(
                                1,
                                int(product["stock"])
                            ),
                            value=1,
                            key=(
                                f"qty_"
                                f"{int(product['id'])}"
                            )
                        )

                        if st.button(
                            "➕ Add",
                            key=(
                                f"add_"
                                f"{int(product['id'])}"
                            ),
                            use_container_width=True
                        ):

                            add_to_cart(
                                int(product["id"]),
                                int(qty)
                            )

                            st.rerun()


    # -------------------------
    # CART
    # -------------------------

    with right:

        st.subheader("🧺 Current Cart")

        df_cart = cart_dataframe()

        if df_cart.empty:

            st.info(
                "Cart is empty."
            )

        else:

            st.dataframe(
                df_cart,
                use_container_width=True,
                hide_index=True
            )

            st.divider()

            subtotal = sum(
                item["price"] *
                item["quantity"]
                for item in
                st.session_state.cart.values()
            )

            customer = st.text_input(
                "Customer Name",
                value="Walk-in Customer"
            )

            discount = st.number_input(
                "Discount (Rs.)",
                min_value=0.0,
                max_value=float(subtotal),
                value=0.0,
                step=100.0
            )

            payment = st.selectbox(
                "Payment Method",
                [
                    "Cash",
                    "Card",
                    "JazzCash",
                    "EasyPaisa",
                    "Bank Transfer"
                ]
            )

            total = subtotal - discount

            st.metric(
                "Grand Total",
                f"Rs. {total:,.0f}"
            )

            if st.button(
                "✅ COMPLETE SALE",
                type="primary",
                use_container_width=True
            ):

                result = save_sale(
                    customer,
                    discount,
                    payment
                )

                if result:

                    st.session_state.last_invoice = result

                    clear_cart()

                    st.success(
                        "Sale completed successfully!"
                    )

                    st.rerun()
