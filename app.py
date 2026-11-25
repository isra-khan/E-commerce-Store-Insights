from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="E-commerce Analytics", page_icon="🛍️", layout="wide")

DATA_PATH = Path(__file__).with_name("Pakistan Largest Ecommerce Dataset.csv.gz")

@st.cache_data(show_spinner="Loading and preparing transaction data…")
def load_data(file_path: str, mtime: float):
    df = pd.read_csv(file_path, low_memory=False)
    # The source file has trailing blank rows and five fully empty columns.
    df = df.dropna(how="all").drop(columns=[c for c in df.columns if c.startswith("Unnamed:") and df[c].isna().all()])
    for col in ["price", "qty_ordered", "grand_total", "discount_amount", "Customer ID", "item_id"]:
        if col in df: df[col] = pd.to_numeric(df[col], errors="coerce")
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    for col in ["category_name_1", "status", "payment_method", "sku"]:
        if col in df: df[col] = df[col].fillna("Unknown").replace({r"^\\N$": "Unknown"}, regex=True)
    df["order_id"] = df["increment_id"].astype("string")
    df["revenue"] = df["grand_total"]
    return df

if not DATA_PATH.exists():
    st.error(f"Dataset not found: {DATA_PATH.name}. Put the compressed CSV beside app.py.")
    st.stop()
df = load_data(str(DATA_PATH), DATA_PATH.stat().st_mtime)
valid_dates = df["created_at"].dropna()

st.markdown("<style>.block-container{padding-top:1.7rem;max-width:1500px}.kpi{background:#111c2d;border:1px solid #26364c;padding:18px 20px;border-radius:14px}.kpi-label{color:#9fb0c4;font-size:13px}.kpi-value{font-size:25px;font-weight:700;color:#f5f8fc;margin-top:6px}.insight{background:#102b35;border-left:4px solid #2dd4bf;padding:12px 16px;border-radius:8px;color:#d8f3ef}</style>", unsafe_allow_html=True)
st.title("🛍️ E-commerce Store Insights")
st.caption("Interactive analytics for the Pakistan Largest Ecommerce dataset · transaction-level records")

with st.sidebar:
    st.header("Filters")
    st.caption(f"{len(df):,} populated rows loaded")
    if not valid_dates.empty:
        dr = st.date_input("Order date range", value=(valid_dates.min().date(), valid_dates.max().date()), min_value=valid_dates.min().date(), max_value=valid_dates.max().date())
    else: dr = None
    cats = sorted(df["category_name_1"].dropna().unique())
    selected_cats = st.multiselect("Product category", cats, default=cats)
    statuses = sorted(df["status"].dropna().unique())
    selected_status = st.multiselect("Order status", statuses, default=statuses)
    payments = sorted(df["payment_method"].dropna().unique())
    selected_pay = st.multiselect("Payment method", payments, default=payments)

f = df.copy()
if dr and len(dr)==2:
    f = f[f["created_at"].dt.date.between(dr[0], dr[1])]
if selected_cats: f = f[f["category_name_1"].isin(selected_cats)]
else: f=f.iloc[0:0]
if selected_status: f=f[f["status"].isin(selected_status)]
else: f=f.iloc[0:0]
if selected_pay: f=f[f["payment_method"].isin(selected_pay)]
else: f=f.iloc[0:0]

# Order-level totals prevent counting each line item as a distinct order.
orders = f.dropna(subset=["order_id"]).groupby("order_id", as_index=False).agg(order_revenue=("grand_total","max"), customer=("Customer ID","first"))
revenue = f["grand_total"].sum()
aov = orders["order_revenue"].mean() if len(orders) else 0
qty = f["qty_ordered"].sum()
cols=st.columns(4)
for c,label,val in zip(cols,["Revenue","Unique orders","Average order value","Units ordered"],[f"PKR {revenue:,.0f}",f"{len(orders):,}",f"PKR {aov:,.0f}",f"{qty:,.0f}"]):
    c.markdown(f'<div class="kpi"><div class="kpi-label">{label}</div><div class="kpi-value">{val}</div></div>',unsafe_allow_html=True)
st.caption(f"Filtered transaction lines: {len(f):,} · Revenue uses line-level grand_total; AOV uses maximum line total per order, matching the notebook’s approach.")

# Fresh session state on each filter change, all chart calculations use filtered rows.
tabs=st.tabs(["Overview","Sales & trends","Categories & products","Customers & payments","Data quality","Statistics & correlation"])
with tabs[0]:
    a,b=st.columns([1.4,1])
    with a:
        if not f.empty and f["created_at"].notna().any():
            trend=f.dropna(subset=["created_at"]).set_index("created_at").resample("MS")["grand_total"].sum().reset_index()
            st.plotly_chart(px.area(trend,x="created_at",y="grand_total",title="Monthly revenue",labels={"created_at":"Month","grand_total":"Revenue (PKR)"},template="plotly_dark"),use_container_width=True)
    with b:
        st.plotly_chart(px.pie(f.groupby("status",as_index=False).size(),names="status",values="size",hole=.55,title="Transaction status mix",template="plotly_dark"),use_container_width=True)
    if len(f):
        top=f.groupby("category_name_1",as_index=False)["grand_total"].sum().sort_values("grand_total",ascending=False)
        top=top[top.category_name_1!="Unknown"].head(1)
        if len(top): st.markdown(f'<div class="insight"><b>Category signal:</b> {top.iloc[0].category_name_1} leads identified categories by filtered revenue (PKR {top.iloc[0].grand_total:,.0f}). Missing category revenue is excluded from this comparison.</div>',unsafe_allow_html=True)
with tabs[1]:
    x,y=st.columns(2)
    dated=f.dropna(subset=["created_at"]).copy()
    monthly=dated.set_index("created_at").resample("MS").agg(revenue=("grand_total","sum"),orders=("order_id","nunique")).reset_index()
    x1=px.line(monthly,x="created_at",y="revenue",markers=True,title="Revenue by month",template="plotly_dark")
    x.plotly_chart(x1,use_container_width=True)
    weekday=dated.assign(weekday=dated.created_at.dt.day_name()).groupby("weekday",as_index=False).agg(revenue=("grand_total","sum"),lines=("item_id","count"))
    weekday["weekday"]=pd.Categorical(weekday.weekday,categories=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],ordered=True); weekday=weekday.sort_values("weekday")
    y.plotly_chart(px.bar(weekday,x="weekday",y="revenue",title="Revenue by weekday",template="plotly_dark"),use_container_width=True)
    st.markdown("Daily patterns are derived from the corrected `created_at` dates; the notebook’s month field is used only in its source analysis and can contain malformed values.")
with tabs[2]:
    cat=f.groupby("category_name_1",as_index=False).agg(revenue=("grand_total","sum"),units=("qty_ordered","sum"),line_items=("item_id","count"),avg_price=("price","mean"))
    cx,cy=st.columns(2)
    cx.plotly_chart(px.bar(cat[cat.category_name_1!="Unknown"].sort_values("revenue").tail(12),x="revenue",y="category_name_1",orientation="h",title="Category revenue (identified categories)",template="plotly_dark"),use_container_width=True)
    sku=f[f.sku!="Unknown"].groupby("sku",as_index=False).agg(revenue=("grand_total","sum"),units=("qty_ordered","sum")).sort_values("revenue",ascending=False).head(15)
    cy.plotly_chart(px.bar(sku.sort_values("revenue"),x="revenue",y="sku",orientation="h",title="Top products by revenue",template="plotly_dark"),use_container_width=True)
    st.dataframe(cat.sort_values("revenue",ascending=False),use_container_width=True,hide_index=True)
with tabs[3]:
    x,y=st.columns(2)
    customer=f.dropna(subset=["Customer ID"]).groupby("Customer ID",as_index=False).agg(revenue=("grand_total","sum"),orders=("order_id","nunique"))
    x.metric("Identified customers",f"{customer['Customer ID'].nunique():,}")
    x.plotly_chart(px.histogram(customer,x="orders",nbins=30,title="Orders per identified customer",template="plotly_dark"),use_container_width=True)
    pay=f.groupby("payment_method",as_index=False).agg(revenue=("grand_total","sum"),lines=("item_id","count"))
    y.plotly_chart(px.bar(pay.sort_values("revenue"),x="revenue",y="payment_method",orientation="h",title="Revenue by payment method",template="plotly_dark"),use_container_width=True)
    st.caption("Customer measures include only rows with a Customer ID; order counts are distinct increment_id values.")
with tabs[4]:
    st.subheader("Missingness in source file")
    missing=df.isna().sum().rename("missing_rows").to_frame(); missing["missing_%"]=(missing.missing_rows/len(df)*100).round(2); missing["dtype"]=df.dtypes.astype(str)
    st.metric("Completely empty source rows removed",f"{1048575-len(df):,}")
    st.dataframe(missing.sort_values("missing_%",ascending=False),use_container_width=True)
    st.caption("Unknown labels in categorical fields represent missing values and are retained so their impact stays visible. Entirely empty Unnamed columns and blank records are excluded from analysis.")
with tabs[5]:
    st.subheader("Filtered descriptive statistics")
    nums=f.select_dtypes("number")
    st.dataframe(nums.describe().T,use_container_width=True)
    if not nums.empty:
        corr=nums.corr(numeric_only=True)
        st.plotly_chart(px.imshow(corr,text_auto=".2f",aspect="auto",color_continuous_scale="RdBu",zmin=-1,zmax=1,title="Numeric correlation matrix",template="plotly_dark"),use_container_width=True)
    if len(f):
        q1,q3=f.grand_total.quantile([.25,.75]); out=((f.grand_total<q1-1.5*(q3-q1))|(f.grand_total>q3+1.5*(q3-q1))).sum()
        st.markdown(f"IQR outlier rule flags **{out:,}** filtered line totals ({out/len(f):.1%}). This is a screening signal; extreme transactions are retained.")
