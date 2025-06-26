import sqlite3
from addData import conn
from langchain.output_parsers import RegexParser
def execute_sql(sql: str):
    conn = sqlite3.connect("ecommerce.db")
    cursor = conn.cursor()

    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]
        return result
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

# def parsing(llm_output):
#     parser = RegexParser(
#     regex=r"(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|WITH)[\s\S]+?;",
#     output_keys=["query"])
#     result = parser.parse(llm_output)
#     sql_query = result["query"].strip()
#     return sql_query
# output = "```sql SELECT name FROM users; ```` This query selects the 'name' column from the 'users' table...."
# def parsing(llm_output):
#     parser = RegexParser(
#         # Match SQL blocks even with newlines, ending at the semicolon
#         regex = r"(SELECT\s.+?;)",
#         output_keys=["query"]
#     )
#     try:
#         result = parser.parse(llm_output)
#         sql_query = result["query"].strip()
#         return sql_query
#     except Exception as e:
#         print(f"Parsing failed: {e}")
#         return "SQL PARSE ERROR"

# parsedquery = parsing(output)
# print(parsedquery)
def split(text:str):
    new=text.strip("")
    return new
sql_query = """
SELECT id, name, email
FROM users
WHERE email LIKE '%@example.com'
LIMIT 10;
"""
test = split(sql_query)
print(test)
print(sql_query)