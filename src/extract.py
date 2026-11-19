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

catetogy_df = extract_categories("retail_store.db")
catetogy_df = validate_categories(catetogy_df)
valid_cat_ids = catetogy_df["CategoryID"]

def validate_products(df,valid_category_ids):
    productID_null = df["ProductID"].isna().sum()
    productName_null = df["ProductName"].isna().sum()
    CategoryID_null = df["CategoryID"].isna().sum()
    productID_duplicated = df["ProductID"].duplicated().sum()
    invalid_category_count = invalid_category_count = (
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


if __name__ == "__main__" :
    db_path = "retail_store.db"

    validated_categories = validate_categories(extract_categories(db_path))
    load_categories(validated_categories)
    valid_cat_ids = validated_categories["CategoryID"]

    validated_products = validate_products(extract_products(db_path), valid_cat_ids)
    load_products(validated_products)

    validated_customers = validate_customers(extract_customers(db_path))
    load_customers(validated_customers)
  