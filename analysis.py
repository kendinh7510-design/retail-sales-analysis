import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# Connect to database
conn = sqlite3.connect("retail_store.db")

print(conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall())
#analysis of total revenue by month
query = """
SELECT strftime('%Y-%m', o.OrderDate) AS Month, 
        ROUND(SUM((od.UnitPrice - (od.UnitPrice *od.DiscountRate)) * od.Quantity),2) AS Total_revenue
        FROM order_details od
        JOIN orders o ON od.OrderID = o.OrderID
        WHERE Month != '2026-06'
        GROUP BY Month
        ORDER BY Month;

"""
df = pd.read_sql(query, conn)

plt.figure(figsize= (12,5))
plt.plot(df['Month'],df["Total_revenue"], marker='o', color='blue')
plt.title("Total Revenue by Month")
plt.xlabel("Month")
plt.ylabel("Total Revenue")
plt.xticks(rotation=90)
plt.tight_layout()
plt.savefig("total_revenue_by_month.png")
plt.show()

#analysis of return rate
query_return_rate = """
 SELECT ROUND(SUM(IsReturned)*100.0 / COUNT(*),2) AS return_rate_pct
        FROM order_details od ;
"""
df_return_rate = pd.read_sql(query_return_rate, conn)
print(df_return_rate)

#analysis of return rate by category
query_return_by_category = """
SELECT cat.CategoryName, ROUND(SUM(IsReturned)*100.0 / COUNT(*), 2) AS return_rate
FROM order_details od
JOIN products p ON od.ProductID = p.ProductID
JOIN categories cat ON p.CategoryID = cat.CategoryID
GROUP BY cat.CategoryName
ORDER BY return_rate DESC
LIMIT 1;
"""
df_return_by_category = pd.read_sql(query_return_by_category, conn)
print(df_return_by_category)

#analysis of most common return reason
query_return_reason = """
SELECT od.ReturnReason, COUNT(od.ReturnReason) AS total
FROM order_details od
WHERE ReturnReason != 'None'
GROUP BY od.ReturnReason
ORDER BY total DESC
LIMIT 5;
"""

df_query_return_reason = pd.read_sql(query_return_reason, conn)
print(df_query_return_reason)

#the most returned product
query_most_returned_product = """
SELECT ProductName, COUNT(*) AS total
FROM products
JOIN order_details ON products.ProductID = order_details.ProductID
WHERE IsReturned = '1'
GROUP BY ProductName
ORDER BY total DESC
LIMIT 1;
"""
df_most_returned_product = pd.read_sql(query_most_returned_product, conn)
print(df_most_returned_product)

plt.figure(figsize=(9, 5))
plt.barh(df_query_return_reason["ReturnReason"], df_query_return_reason["total"], color="orange")
plt.title("Top 5 return reasons")
plt.xlabel("total number of returns")
plt.ylabel("return reasons")
plt.gca().invert_yaxis()
plt.tight_layout()
plt.savefig("chart_return_reasons.png")
plt.show()

conn.close()