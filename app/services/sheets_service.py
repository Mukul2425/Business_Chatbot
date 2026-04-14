# import pandas as pd
# from app.config import GOOGLE_SHEET_CSV_URL

# faq_df = None

# def load_faq():
#     global faq_df
#     faq_df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
#     faq_df.fillna("", inplace=True)


# def get_faq():
#     return faq_df


import pandas as pd

FAQ_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRnZpyvte5-e3U3PyMd1Ipp0p3A7qyQXQJWGTk3eLnCl3lxZrf0tZANgy7LnwqQuqzUmVTV5jBrHpGz/pub?gid=0&single=true&output=csv"

SERVICES_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRnZpyvte5-e3U3PyMd1Ipp0p3A7qyQXQJWGTk3eLnCl3lxZrf0tZANgy7LnwqQuqzUmVTV5jBrHpGz/pub?gid=1649550237&single=true&output=csv"
PRICING_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRnZpyvte5-e3U3PyMd1Ipp0p3A7qyQXQJWGTk3eLnCl3lxZrf0tZANgy7LnwqQuqzUmVTV5jBrHpGz/pub?gid=392725975&single=true&output=csv"
INVENTORY_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRnZpyvte5-e3U3PyMd1Ipp0p3A7qyQXQJWGTk3eLnCl3lxZrf0tZANgy7LnwqQuqzUmVTV5jBrHpGz/pub?gid=1863099290&single=true&output=csv"
CONTACT_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRnZpyvte5-e3U3PyMd1Ipp0p3A7qyQXQJWGTk3eLnCl3lxZrf0tZANgy7LnwqQuqzUmVTV5jBrHpGz/pub?gid=250930195&single=true&output=csv"

faq_df = None 
services_df = None 
pricing_df = None 
inventory_df = None 
contact_df = None
def load_all_data(): 
    global faq_df, services_df, pricing_df, inventory_df, contact_df
    faq_df = pd.read_csv(FAQ_URL).fillna("")
    services_df = pd.read_csv(SERVICES_URL).fillna("")
    pricing_df = pd.read_csv(PRICING_URL).fillna("")
    inventory_df = pd.read_csv(INVENTORY_URL).fillna("")
    contact_df = pd.read_csv(CONTACT_URL).fillna("")

def get_faq(): return faq_df
def get_services(): return services_df
def get_pricing(): return pricing_df
def get_inventory(): return inventory_df
def get_contact(): return contact_df