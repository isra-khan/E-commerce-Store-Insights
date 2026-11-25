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
    source_missing = df.isna().sum()
    for col in ["price", "qty_ordered", "grand_total", "discount_amount", "Customer ID", "item_id"]:
        if col in df: df[col] = pd.to_numeric(df[col], errors="coerce")
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    for col in ["category_name_1", "status", "payment_method", "sku"]:
        if col in df: df[col] = df[col].fillna("Unknown").replace({r"^\\N$": "Unknown"}, regex=True)
    df["order_id"] = df["increment_id"].astype("string")
    df["merchandise_value"] = df["price"] * df["qty_ordered"]
    return df, source_missing

if not DATA_PATH.exists():
    st.error(f"Dataset not found: {DATA_PATH.name}. Put the compressed CSV beside app.py.")
    st.stop()
df, source_missing = load_data(str(DATA_PATH), DATA_PATH.stat().st_mtime)
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
    default_statuses = ["complete"] if "complete" in statuses else statuses
    selected_status = st.multiselect("Order status", statuses, default=default_statuses)
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

# grand_total repeats on each line in an order; max takes its single order-level value.
orders = f.dropna(subset=["order_id"]).groupby("order_id", as_index=False).agg(order_value=("grand_total","max"))
order_value = orders["order_value"].sum()
aov = order_value / len(orders) if len(orders) else 0
merchandise_value = f["merchandise_value"].sum()
qty = f["qty_ordered"].sum()
cols=st.columns(4)
for c,label,val in zip(cols,["Merchandise value (price × qty)","Deduplicated order value","Unique orders","Average order value"],[f"PKR {merchandise_value:,.0f}",f"PKR {order_value:,.0f}",f"{len(orders):,}",f"PKR {aov:,.0f}"]):
    c.markdown(f'<div class="kpi"><div class="kpi-label">{label}</div><div class="kpi-value">{val}</div></div>',unsafe_allow_html=True)
st.caption(f"Filtered transaction lines: {len(f):,} · Merchandise value is price × quantity before discounts. Order value uses grand_total once per matching order; AOV is deduplicated order value divided by matching orders. The default status filter is complete.")

# Fresh session state on each filter change, all chart calculations use filtered rows.
tabs=st.tabs(["Overview","Sales & trends","Categories & products","Customers & payments","Data quality","Statistics & correlation"])
with tabs[0]:
    a,b=st.columns([1.4,1])
    with a:
        if not f.empty and f["created_at"].notna().any():
            trend=f.dropna(subset=["created_at"]).set_index("created_at").resample("MS")["merchandise_value"].sum().reset_index()
            st.plotly_chart(px.area(trend,x="created_at",y="merchandise_value",title="Monthly merchandise value",labels={"created_at":"Month","merchandise_value":"Merchandise value (PKR)"},template="plotly_dark"),use_container_width=True)
    with b:
        status_data = df
        if dr and len(dr)==2:
            status_data = status_data[status_data["created_at"].dt.date.between(dr[0], dr[1])]
        if selected_cats:
            status_data = status_data[status_data["category_name_1"].isin(selected_cats)]
        else:
            status_data = status_data.iloc[0:0]
        if selected_pay:
            status_data = status_data[status_data["payment_method"].isin(selected_pay)]
        else:
            status_data = status_data.iloc[0:0]
        status_counts = status_data.groupby("status")["order_id"].nunique().rename("orders").reset_index()
        st.plotly_chart(px.pie(status_counts,names="status",values="orders",hole=.55,title="Order status mix (all statuses)",template="plotly_dark"),use_container_width=True)
    if len(f):
        top=f.groupby("category_name_1",as_index=False)["merchandise_value"].sum().sort_values("merchandise_value",ascending=False)
        top=top[top.category_name_1!="Unknown"].head(1)
        if len(top): st.markdown(f'<div class="insight"><b>Category signal:</b> {top.iloc[0].category_name_1} leads identified categories by filtered merchandise value (PKR {top.iloc[0].merchandise_value:,.0f}). Missing category value is excluded from this comparison.</div>',unsafe_allow_html=True)
with tabs[1]:
    x,y=st.columns(2)
    dated=f.dropna(subset=["created_at"]).copy()
    monthly=dated.set_index("created_at").resample("MS").agg(merchandise_value=("merchandise_value","sum"),orders=("order_id","nunique")).reset_index()
    x1=px.line(monthly,x="created_at",y="merchandise_value",markers=True,title="Merchandise value by month",template="plotly_dark")
    x.plotly_chart(x1,use_container_width=True)
    weekday=dated.assign(weekday=dated.created_at.dt.day_name()).groupby("weekday",as_index=False).agg(merchandise_value=("merchandise_value","sum"),lines=("item_id","count"))
    weekday["weekday"]=pd.Categorical(weekday.weekday,categories=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],ordered=True); weekday=weekday.sort_values("weekday")
    y.plotly_chart(px.bar(weekday,x="weekday",y="merchandise_value",title="Merchandise value by weekday",template="plotly_dark"),use_container_width=True)
    st.markdown("Daily patterns are derived from the corrected `created_at` dates; the notebook’s month field is used only in its source analysis and can contain malformed values.")
with tabs[2]:
    cat=f.groupby("category_name_1",as_index=False).agg(merchandise_value=("merchandise_value","sum"),units=("qty_ordered","sum"),line_items=("item_id","count"),avg_price=("price","mean"))
    cx,cy=st.columns(2)
    cx.plotly_chart(px.bar(cat[cat.category_name_1!="Unknown"].sort_values("merchandise_value").tail(12),x="merchandise_value",y="category_name_1",orientation="h",title="Category merchandise value (identified categories)",template="plotly_dark"),use_container_width=True)
    sku=f[f.sku!="Unknown"].groupby("sku",as_index=False).agg(merchandise_value=("merchandise_value","sum"),units=("qty_ordered","sum")).sort_values("merchandise_value",ascending=False).head(15)
    cy.plotly_chart(px.bar(sku.sort_values("merchandise_value"),x="merchandise_value",y="sku",orientation="h",title="Top products by merchandise value",template="plotly_dark"),use_container_width=True)
    st.dataframe(cat.sort_values("merchandise_value",ascending=False),use_container_width=True,hide_index=True)
with tabs[3]:
    x,y=st.columns(2)
    customer=f.dropna(subset=["Customer ID"]).groupby("Customer ID",as_index=False).agg(merchandise_value=("merchandise_value","sum"),orders=("order_id","nunique"))
    x.metric("Identified customers",f"{customer['Customer ID'].nunique():,}")
    x.plotly_chart(px.histogram(customer,x="orders",nbins=30,title="Orders per identified customer",template="plotly_dark"),use_container_width=True)
    pay=f.groupby("payment_method",as_index=False).agg(merchandise_value=("merchandise_value","sum"),lines=("item_id","count"))
    y.plotly_chart(px.bar(pay.sort_values("merchandise_value"),x="merchandise_value",y="payment_method",orientation="h",title="Merchandise value by payment method",template="plotly_dark"),use_container_width=True)
    st.caption("Customer measures include only rows with a Customer ID; order counts are distinct increment_id values. Merchandise value is assigned to individual transaction lines.")
with tabs[4]:
    st.subheader("Missingness in source file")
    missing=source_missing.rename("missing_rows").to_frame(); missing["missing_%"]=(missing.missing_rows/len(df)*100).round(2); missing["dtype"]=df.dtypes.astype(str)
    st.metric("Completely empty source rows removed",f"{1048575-len(df):,}")
    st.dataframe(missing.sort_values("missing_%",ascending=False),use_container_width=True)
    st.caption("Missingness is measured before categorical nulls are replaced with Unknown. Counts cover populated source records; entirely blank rows and fully empty columns are excluded.")
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
