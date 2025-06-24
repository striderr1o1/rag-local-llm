import chromadb
import logging
import os
import logging
import requests

schema_text = """
Table: users (id, name, email)
Table: orders (id, user_id, amount, date)
Table: products (id, name, price)
"""

#STEP 1: CHUNK DATA

