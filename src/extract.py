import pandas as pd
import sqlite3
import psycopg
import os
from dotenv import load_dotenv
load_dotenv()


username = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
def connect_postgres():
    conn =psycopg.connect(
        host="localhost",
        port=5432,
        dbname="retail_etl",
        user= username,
        password = password
    )
    return conn

def extract_categories(db_path):
    connect = sqlite3.connect(db_path)
    try:
        query = """
            SELECT * FROM categories;
     """
        df = pd.read_sql(query,connect)
    finally:
        connect.close()
    return df


def extract_products(db_path):
    connect = sqlite3.connect(db_path)
    try:
        query = """ SELECT * FROM products; """
        df = pd.read_sql(query,connect)

    finally:
        connect.close()
    return df


def extract_customers(db_path):
    connect = sqlite3.connect(db_path)
    try:
        query = """SELECT * FROM customers ;"""
        df = pd.read_sql(query,connect)
    finally:
        connect.close()
    return df

def extract_orders(df_path):
    connect = sqlite3.connect(df_path)
    try:
        query = """SELECT * FROM orders ;"""
        df = pd.read_sql(query,connect)
    finally:
        connect.close()
    return df

def extract_order_details(df_path):
    connect = sqlite3.connect(df_path)
    try:
        query = "SELECT * FROM order_details"
        df = pd.read_sql(query,connect)
    finally:
        connect.close()
    return df

def validate_categories(df):
    categoryID_null = df["CategoryID"].isna().sum()
    duplicate = df["CategoryID"].duplicated().sum()
    categoryName_null = df["CategoryName"].isna().sum()
    total_sum = categoryID_null+ duplicate + categoryName_null
    if total_sum > 0:
        raise ValueError(
            "Category validation failed:"
            f"CatogryID has: {categoryID_null} null " 
            f"CategoryID has {duplicate} duplicated "
            f"CategoryName has {categoryName_null} null"
        )
    return df

def validate_products(df,valid_category_ids):
    productID_null = df["ProductID"].isna().sum()
    productName_null = df["ProductName"].isna().sum()
    CategoryID_null = df["CategoryID"].isna().sum()
    productID_duplicated = df["ProductID"].duplicated().sum()
    invalid_category_count = (
    df["CategoryID"].notna() & ~df["CategoryID"].isin(valid_category_ids)).sum()

    total_error = productID_null+productName_null+ CategoryID_null+ productID_duplicated+ invalid_category_count
    if total_error > 0:
        raise ValueError(
            "Products validation failed:"
            f"ProductID has: {productID_null} null "
            f"ProductName has: {productName_null} null "
            f"CategoryID has: {CategoryID_null} null "
            f"ProductID has: {productID_duplicated} duplicated "
            f"CategoryID has: {invalid_category_count} invalid "
        )
    return df 

def validate_customers(df):
    
    customerID_null = df["CustomerID"].isna().sum()
    customerID_duplicated = df["CustomerID"].duplicated().sum()
    invalid_age_count = ((df["Age"] < 18) | (df["Age"] > 120)).sum()
    age_null = df["Age"].isna().sum()
    gender_null = df["Gender"].isna().sum()
    city_null = df["City"].isna().sum()
    region_null = df["Region"].isna().sum()
    customer_segment_null = df["CustomerSegment"].isna().sum()
    parsed_dates = pd.to_datetime(df["SignUpDate"], format= "%Y-%m-%d", errors = 'coerce') 
    invalid_date_count = parsed_dates.isna().sum()

    total_errors = (
        customerID_null
        + customerID_duplicated
        + invalid_age_count
        + age_null
        + gender_null
        + city_null
        + region_null
        + customer_segment_null
        + invalid_date_count
    )
    if total_errors > 0:
        raise ValueError(
            "Customer validation failed: "
            f"CustomerID has {customerID_null} null and "
            f"{customerID_duplicated} duplicated; "
            f"Age has {age_null} null and {invalid_age_count} outside 18-120; "
            f"Gender has {gender_null} null; "
            f"City has {city_null} null; "
            f"Region has {region_null} null; "
            f"CustomerSegment has {customer_segment_null} null; "
            f"SignUpDate has {invalid_date_count} invalid or missing."
        )

    validated_df = df.copy()
    validated_df["SignUpDate"] = parsed_dates.dt.date
    return validated_df

def validate_orders(df, valid_customer_ids):
    orderId_null = df["OrderID"].isna().sum()
    orderId_duplicated = df["OrderID"].duplicated().sum()
    invalid_customer_count = (~df["CustomerID"].isin(valid_customer_ids) & (df["CustomerID"].notna())).sum()
    customerID_null = (~df["CustomerID"].notna()).sum()
    parsed_order_dates = pd.to_datetime(df["OrderDate"], format= "%Y-%m-%d", errors = "coerce")
    invalid_order_dates = parsed_order_dates.isna().sum()
    parsed_order_times = pd.to_datetime(df["OrderTime"], format = "%H:%M:%S", errors = "coerce")
    invalid_order_times = parsed_order_times.isna().sum()

    total_errors = (
        orderId_null
        + orderId_duplicated
        + invalid_customer_count
        + customerID_null
        + invalid_order_dates
        + invalid_order_times
    )
    if total_errors > 0:
        raise ValueError(
            "Order validation failed: "
            f"OrderID has {orderId_null} missing and {orderId_duplicated} duplicated; "
            f"CustomerID has {customerID_null} missing and "
            f"{invalid_customer_count} not found in customers; "
            f"OrderDate has {invalid_order_dates} invalid or missing; "
            f"OrderTime has {invalid_order_times} invalid or missing."
        )
    validated_df = df.copy()
    validated_df["OrderDate"] = parsed_order_dates.dt.date
    validated_df["OrderTime"] = parsed_order_times.dt.time
    return validated_df

def validate_order_details(df, valid_order_ids, valid_product_ids):
    order_id_null = df["OrderID"].isna().sum()
    product_id_null = df["ProductID"].isna().sum()
    order_detail_duplicated = df.duplicated(
        subset=["OrderID", "ProductID"]
    ).sum()
    invalid_order_count = (
        ~df["OrderID"].isin(valid_order_ids) & df["OrderID"].notna()
    ).sum()
    invalid_product_count = (
        ~df["ProductID"].isin(valid_product_ids) & df["ProductID"].notna()
    ).sum()
    quantity_null = df["Quantity"].isna().sum()
    unit_cost_null = df["UnitCost"].isna().sum()
    unit_price_null = df["UnitPrice"].isna().sum()
    discount_rate_null = df["DiscountRate"].isna().sum()
    is_returned_null = df["IsReturned"].isna().sum()
    invalid_quantity_count = (
        df["Quantity"].notna() & (df["Quantity"] <= 0)
    ).sum()
    invalid_unit_cost_count = (
        df["UnitCost"].notna() & (df["UnitCost"] < 0)
    ).sum()
    invalid_unit_price_count = (
        df["UnitPrice"].notna() & (df["UnitPrice"] < 0)
    ).sum()
    invalid_discount_count= (df["DiscountRate"].notna()& (
        (df["DiscountRate"] < 0)| (df["DiscountRate"] > 1)
    )
).sum()
    invalid_is_returned = (
        df["IsReturned"].notna() & ~df["IsReturned"].isin([0, 1])
    ).sum()

    returned_rows = df["IsReturned"].eq(1)
    parsed_return_date = pd.to_datetime(
        df["ReturnDate"], format="%Y-%m-%d", errors="coerce"
    )
    return_date_missing = (
        returned_rows & parsed_return_date.isna()
    ).sum()
    parsed_return_time = pd.to_datetime(
        df["ReturnTime"], format="%H:%M:%S", errors="coerce"
    )
    return_time_missing = (
        returned_rows & parsed_return_time.isna()
    ).sum()
    return_reason_null = (
        returned_rows
        & (
            df["ReturnReason"].isna()
            | df["ReturnReason"].astype("string").str.strip().eq("").fillna(False)
        )
    ).sum()
    total_errors = (
        order_id_null
        + product_id_null
        + order_detail_duplicated
        + invalid_order_count
        + invalid_product_count
        + quantity_null
        + invalid_quantity_count
        + unit_cost_null
        + invalid_unit_cost_count
        + unit_price_null
        + invalid_unit_price_count
        + discount_rate_null
        + invalid_discount_count
        + is_returned_null
        + invalid_is_returned
        + return_date_missing
        + return_time_missing
        + return_reason_null
    )
    if total_errors > 0:
        raise ValueError(
            "Order details validation failed: "
            f"OrderID has {order_id_null} missing; "
            f"(OrderID, ProductID) has {order_detail_duplicated} duplicated pairs; "
            f"{invalid_order_count} not found in orders; "
            f"ProductID has {product_id_null} missing and "
            f"{invalid_product_count} not found in products; "
            f"Quantity has {quantity_null} missing and "
            f"{invalid_quantity_count} values not greater than 0; "
            f"UnitCost has {unit_cost_null} missing and "
            f"{invalid_unit_cost_count} negative values; "
            f"UnitPrice has {unit_price_null} missing and "
            f"{invalid_unit_price_count} negative values; "
            f"DiscountRate has {discount_rate_null} missing and "
            f"{invalid_discount_count} values outside 0-1; "
            f"IsReturned has {is_returned_null} missing and "
            f"{invalid_is_returned} values other than 0 or 1; "
            f"ReturnDate has {return_date_missing} invalid or missing for returned rows; "
            f"ReturnTime has {return_time_missing} invalid or missing for returned rows; "
            f"ReturnReason has {return_reason_null} missing for returned rows."
        )

    validated_df = df.copy()
    validated_df["IsReturned"] = validated_df["IsReturned"].astype(bool)
    validated_df["ReturnDate"] = parsed_return_date.dt.date
    validated_df["ReturnTime"] = parsed_return_time.dt.time
    return validated_df

def load_categories(df):
    conn = connect_postgres()
    inserted_row =0
    try:
        with conn.cursor() as cursor:
            for row in df.itertuples(index=False):
                cursor.execute("""INSERT INTO categories (CategoryID, CategoryName)""" \
                """ VALUES(%s,%s) ON CONFLICT (CategoryID)   DO NOTHING""" ,(row.CategoryID, row.CategoryName))
                inserted_row += cursor.rowcount

            conn.commit()
            print(f"INSERTED {inserted_row} line")
    except Exception:
            conn.rollback()
            raise 
    finally:
        conn.close()        
def load_products(df):
    conn = connect_postgres()
    affected_rows = 0
    try:
        with conn.cursor() as cursor:
            for row in df.itertuples(index=False):
                cursor.execute("""
                INSERT INTO products (ProductID,ProductName,CategoryID) VALUES(%s,%s,%s)
                  ON CONFLICT (ProductID) DO UPDATE SET ProductName = EXCLUDED.ProductName , CategoryID = EXCLUDED.CategoryID 
                  WHERE products.productname IS DISTINCT FROM EXCLUDED.productname
                  OR products.categoryid IS DISTINCT FROM EXCLUDED.categoryid;
                  """, (row.ProductID,row.ProductName,row.CategoryID))
                affected_rows += cursor.rowcount
            conn.commit()
            print(f"Rows affected: {affected_rows} ")
    except Exception:
            conn.rollback()
            raise 
    finally:
        conn.close()

def load_customers(df):
    conn = connect_postgres()
    affected_rows = 0
    try:
        with conn.cursor() as cursor:
            for row in df.itertuples(index =False):
                cursor.execute(""" 
            INSERT INTO customers (customerid,gender,age,city,region,customersegment,signupdate)
            VALUES(%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (customerid) DO UPDATE SET gender = EXCLUDED.gender,
            age =  EXCLUDED.age,city = EXCLUDED.city, region = EXCLUDED.region,
              customersegment = EXCLUDED.customersegment,
            signupdate = EXCLUDED.signupdate
            WHERE customers.gender IS DISTINCT FROM EXCLUDED.gender
            OR customers.age IS DISTINCT FROM EXCLUDED.age
            OR customers.city IS DISTINCT FROM EXCLUDED.city
            OR customers.region IS DISTINCT FROM EXCLUDED.region
            OR customers.customersegment IS DISTINCT FROM EXCLUDED.customersegment
            OR customers.signupdate IS DISTINCT FROM EXCLUDED.signupdate
""", (row.CustomerID,row.Gender,row.Age,row.City,row.Region,row.CustomerSegment,row.SignUpDate)
)
                affected_rows += cursor.rowcount
        conn.commit()
        print(f"Rows affected: {affected_rows}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def load_orders(df):
    conn = connect_postgres()
    affected_rows = 0
    try:
        with conn.cursor() as cursor:
            for row in df.itertuples(index=False):
                cursor.execute(
                    "SELECT customerid FROM orders WHERE orderid = %s",
                    (row.OrderID,),
                )
                existing_order = cursor.fetchone()
                if existing_order is not None and existing_order[0] != row.CustomerID:
                    raise ValueError(f"CustomerID conflict for OrderID {row.OrderID}")
                cursor.execute(
                    """
                    INSERT INTO orders (orderid, customerid, orderdate, ordertime)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (orderid) DO UPDATE
                    SET orderdate = EXCLUDED.orderdate,
                        ordertime = EXCLUDED.ordertime
                    WHERE orders.orderdate IS DISTINCT FROM EXCLUDED.orderdate
                       OR orders.ordertime IS DISTINCT FROM EXCLUDED.ordertime
                    """,
                    (row.OrderID, row.CustomerID, row.OrderDate, row.OrderTime),
                )
                affected_rows += cursor.rowcount
        conn.commit()
        print(f"Rows affected: {affected_rows}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def load_order_details(df):
    conn = connect_postgres()
    affected_rows =0
    try:
        with conn.cursor() as cursor:
            for row in df.itertuples(index=False):
                cursor.execute(
                """
                    INSERT INTO order_details (
                        orderid, productid, quantity, unitcost, unitprice,
                        discountrate, isreturned, returndate, returntime,
                        returnreason
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (orderid, productid) DO UPDATE SET
                        quantity = EXCLUDED.quantity,
                        unitcost = EXCLUDED.unitcost,
                        unitprice = EXCLUDED.unitprice,
                        discountrate = EXCLUDED.discountrate,
                        isreturned = EXCLUDED.isreturned,
                        returndate = EXCLUDED.returndate,
                        returntime = EXCLUDED.returntime,
                        returnreason = EXCLUDED.returnreason
                    WHERE order_details.quantity IS DISTINCT FROM EXCLUDED.quantity
                    OR order_details.unitcost IS DISTINCT FROM EXCLUDED.unitcost
                    OR order_details.unitprice IS DISTINCT FROM EXCLUDED.unitprice
                    OR order_details.discountrate IS DISTINCT FROM EXCLUDED.discountrate
                    OR order_details.isreturned IS DISTINCT FROM EXCLUDED.isreturned
                    OR order_details.returndate IS DISTINCT FROM EXCLUDED.returndate
                    OR order_details.returntime IS DISTINCT FROM EXCLUDED.returntime
                    OR order_details.returnreason IS DISTINCT FROM EXCLUDED.returnreason
                    """, (row.OrderID,row.ProductID,row.Quantity,row.UnitCost,row.UnitPrice,row.DiscountRate,
                          bool(row.IsReturned),
                          None if pd.isna(row.ReturnDate) else row.ReturnDate,
                          None if pd.isna(row.ReturnTime) else row.ReturnTime,
                          None if pd.isna(row.ReturnReason) else row.ReturnReason)
                    )
                affected_rows += cursor.rowcount
            conn.commit()
            print(f"Rows affected: {affected_rows}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    db_path = "retail_store.db"

    categories_df = extract_categories(db_path)
    validated_categories = validate_categories(categories_df)

    products_df = extract_products(db_path)
    valid_category_ids = validated_categories["CategoryID"]
    validated_products = validate_products(products_df, valid_category_ids)

    customers_df = extract_customers(db_path)
    validated_customers = validate_customers(customers_df)

    orders_df = extract_orders(db_path)
    valid_customer_ids = validated_customers["CustomerID"]
    validated_orders = validate_orders(orders_df, valid_customer_ids)

    order_details_df = extract_order_details(db_path)
    valid_order_ids = validated_orders["OrderID"]
    valid_product_ids = validated_products["ProductID"]
    validated_order_details = validate_order_details(
        order_details_df, valid_order_ids, valid_product_ids
    )

    load_categories(validated_categories)
    load_products(validated_products)
    load_customers(validated_customers)
    load_orders(validated_orders)
    load_order_details(validated_order_details)
  