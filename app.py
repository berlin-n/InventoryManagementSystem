import streamlit as st
from supabase import create_client, Client
import pandas as pd

SUPABASE_URL = "https://snjqfrclsqdaflmrljbn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNuanFmcmNsc3FkYWZsbXJsamJuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDc5NDU0MDIsImV4cCI6MjA2MzUyMTQwMn0.jKjH8iro6NlZr18c-7nKVn0Vp8F06YRMXWzqC4lXobQ"

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

# create_tables()

st.title("🧾 Inventory Management System")

menu = ["Add Product", "Add Customer", "View Inventory", "Make Sale", "Restock Products","View Sales"]
choice = st.sidebar.selectbox("Menu", menu)
columns = ["name", "quantity", "flavour"]

def get_sales_data():
    response = supabase.from_("sales").select(
    "quantity_sold, created_at, product_id, customer_id, "
    "products(name, flavour), customers(name)"
).execute()

    # if response.error:
    #     st.error(f"Error fetching sales: {response.error.message}")
    #     return pd.DataFrame()

    sales = response.data

    # Transform to a DataFrame
    rows = []
    for sale in sales:
        rows.append({
            "Customer": sale["customers"]["name"],
            "Product": f"{sale['products']['name']} ({sale['products']['flavour']})",
            "Quantity Sold": sale["quantity_sold"],
            "Date": pd.to_datetime(sale["created_at"]).strftime("%Y-%m-%d %H:%M"),
        })

    return pd.DataFrame(rows)

if choice == "Add Product":
    st.subheader("➕ Add New Product")

    name = st.text_input("Product Name")
    flavour = st.text_input("Flavour")
    quantity = st.number_input("Initial Quantity", min_value=1, step=1)

    if st.button("Add Product"):
        if name and flavour:
            supabase.table("products").insert({
                "name": name,
                "flavour": flavour,
                "quantity": quantity
            }).execute()
            st.success(f"Product '{name}' ({flavour}) added with {quantity} units.")
        else:
            st.error("Product name and flavour are required.")


elif choice == "View Inventory":
    st.subheader("📦 Inventory")

    data = supabase.table("products").select("*").execute().data
    if data:
        df = pd.DataFrame(data)
        df = df[["name", "flavour", "quantity"]]
        df.columns = ["Product", "Flavour", "Quantity Left"]
        st.dataframe(df)
    else:
        st.info("No products available.")

elif choice == "Add Customer":
    st.subheader("👤 Add New Customer")

    name = st.text_input("Customer Name")
    email = st.text_input("Customer Email (optional)")

    if st.button("Add Customer"):
        if name:
            supabase.table("customers").insert({
                "name": name,
                "email": email
            }).execute()
            st.success(f"Customer '{name}' added.")
        else:
            st.warning("Customer name is required.")


elif choice == "Make Sale":
    st.subheader("🛒 Record a Sale")

    # Step 1: Load products
    products_data = supabase.table("products").select("*").execute().data
    if not products_data:
        st.warning("No products available.")
        st.stop()

    product_options = [f"{p['name']} ({p['flavour']})" for p in products_data]
    selected_label = st.selectbox("Select Product + Flavour", product_options)

    selected_product = next((p for p in products_data if f"{p['name']} ({p['flavour']})" == selected_label), None)
    if not selected_product:
        st.error("Product not found.")
        st.stop()

    product_id = selected_product["id"]
    current_qty = selected_product["quantity"]
    st.write(f"Available Quantity: **{current_qty}**")

    qty_to_sell = st.number_input("Quantity to Sell", min_value=1, max_value=current_qty, step=1)

    # Step 2: Load customers
    customers = supabase.table("customers").select("*").execute().data or []
    if not customers:
        st.warning("No customers available. Please add a customer first.")
        st.stop()

    customer_names = [c["name"] for c in customers]
    selected_customer_name = st.selectbox("Select Customer", customer_names)

    customer = next((c for c in customers if c["name"] == selected_customer_name), None)
    if not customer:
        st.error("Customer not found.")
        st.stop()

    customer_id = customer["id"]

    # Step 3: Confirm Sale
    if st.button("Confirm Sale"):
        try:
            # Update product quantity
            new_qty = current_qty - qty_to_sell
            supabase.table("products").update({
                "quantity": new_qty
            }).eq("id", product_id).execute()

            # Record sale
            supabase.table("sales").insert({
                "product_id": product_id,
                "customer_id": customer_id,
                "quantity_sold": qty_to_sell
            }).execute()

            st.success(f"✅ Sold {qty_to_sell} unit(s) of {selected_product['name']} ({selected_product['flavour']}) to {selected_customer_name}")

        except Exception as e:
            st.error(f"Error processing sale: {e}")

elif choice == "View Sales":
    with st.expander("📊 View All Sales"):
        sales_df = get_sales_data()
        if not sales_df.empty:
            st.dataframe(sales_df, use_container_width=True)
        else:
            st.info("No sales data available yet.")

elif choice == "Restock Products":
    st.header("Restock Product")

    # Fetch all products
    products_data = supabase.from_("products").select("id, name, flavour, quantity").execute().data

    if products_data:
        product_options = {f"{p['name']} - {p['flavour']}": p['id'] for p in products_data}
        selected_product = st.selectbox("Select Product to Restock", list(product_options.keys()))

        restock_amount = st.number_input("How many units are you adding?", min_value=1, step=1)

        if st.button("Add Stock"):
            product_id = product_options[selected_product]

            # Get current quantity
            current_quantity = next(p["quantity"] for p in products_data if p["id"] == product_id)
            new_quantity = current_quantity + restock_amount

            # Update in Supabase
            update_response = supabase.from_("products").update({"quantity": new_quantity}).eq("id", product_id).execute()
            st.success(f"{restock_amount} units added to {selected_product}. New quantity: {new_quantity}")
            # if update_response.error:
            #     st.error("Failed to restock product.")
            # else:
            #     st.success(f"{restock_amount} units added to {selected_product}. New quantity: {new_quantity}")
    else:
        st.warning("No products found.")


