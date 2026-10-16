import pandas as pd


# In[6]:


df=pd.read_csv(r"C:\Users\shivi\Downloads\customer_shopping_behavior.csv")


# In[7]:


df


# In[35]:


pd.set_option('display.max_rows', 30)
df


# In[25]:


df.head(10)


# In[28]:


df.info()


# In[32]:


df.describe(include='all')


# In[36]:


df.isnull().sum()


# In[37]:


df['Review Rating']=df.groupby('Category')['Review Rating'].transform(lambda x:x.fillna(x.median()))


# In[38]:


df.isnull().sum()


# In[74]:


df = df.rename(columns={
    'customerid': 'customer_id',
    'itempurchased': 'item_purchased',
    'purchaseamount(usd)': 'purchase_amount',
    'reviewrating': 'review_rating',
    'subscriptionstatus': 'subscription_status',
    'shippingtype': 'shipping_type',
    'discountapplied': 'discount_applied',
    'promocodeused': 'promocode_used',
    'previouspurchases': 'previous_purchases',
    'paymentmethod': 'payment_method',
    'frequencyofpurchases': 'frequency_of_purchases'
})
df.columns


# In[76]:


# creating a new column age group
labels=['Young','Adult','Middle_aged','Senior']
df['age_group']=pd.qcut(df['age'],q=4,labels=labels)


# In[77]:


df['age_group']


# In[81]:


df[['age','age_group']].head(15)


# In[83]:


# creating column purchase_frequency_in_days
frequency_mapping={'Weekly':7,'Fortnightly':14,'Monthly':30,'Bi-Weekly':14,'Quarterly':90,'Every 3 months':90,'Annually':365}
df['purchase_frequency_in_days']=df['frequency_of_purchases'].map(frequency_mapping)
df[['purchase_frequency_in_days','frequency_of_purchases']].head(100)


# In[84]:


(df['discount_applied']==df['promocode_used']).all()


# In[86]:


df=df.drop('promocode_used',axis=1)


# In[87]:


df.columns


# In[88]:


pip install sqlalchemy


# In[91]:


import pyodbc

print(pyodbc.drivers())


# In[93]:


import pandas as pd
import pyodbc
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

# 1. Database connection details
SERVER = r'localhost\SQLEXPRESS'
DATABASE = 'Customer_Behaviour'

# 2. Create the connection string
connection_string = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

# 3. Create the SQLAlchemy engine
connection_url = URL.create(
    "mssql+pyodbc",
    query={"odbc_connect": connection_string}
)

engine = create_engine(connection_url)

print("Connection engine created.")


# In[94]:


from sqlalchemy import text

with engine.connect() as connection:
    result = connection.execute(
        text("SELECT @@SERVERNAME AS ServerName, DB_NAME() AS DatabaseName")
    )

    print(result.fetchone())


# In[95]:


df.to_sql(
    name='Customers',
    con=engine,
    schema='dbo',
    if_exists='replace',
    index=False
)
