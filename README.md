# E-commerce Store Insights Dashboard

Interactive Streamlit dashboard for the Pakistan Largest Ecommerce dataset. It covers sales, products, customers, payment methods, data quality, descriptive statistics, and correlations. All charts and KPIs respond to sidebar date, category, status, and payment filters.

## Run locally

1. Create/activate a Python 3.10+ environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Keep `Pakistan Largest Ecommerce Dataset.csv.gz` beside `app.py`.
4. Start: `streamlit run app.py`

The original source notebook and CSV are left unchanged locally; the repository uses a compressed CSV copy to stay below GitHub's per-file size limit. Blank source rows and fully empty `Unnamed` columns are removed at load time. Missing categorical values display as `Unknown`, while the data-quality view measures missingness before that replacement. Merchandise value is calculated from line-level `price × qty_ordered` (before discounts). `grand_total` is counted once per order for deduplicated order value and AOV. The dashboard defaults to `complete` orders; other statuses can be selected in the sidebar.

## Deploy

Deploy on Streamlit Community Cloud by connecting this repository, selecting `app.py` as the main file, and keeping the compressed CSV in the repository (or replace `DATA_PATH` with a secure uploaded/private data source). For private data, use Streamlit secrets or a storage service and avoid committing the data.

## Notes on interpretation

The source has substantial missingness (including missing product categories). The dashboard exposes missingness and excludes `Unknown` from identified-category rankings. The notebook reported November as the strongest month, and Electronics as a growth opportunity; the supplied data uses `Entertainment` and does not contain an `Electronics` category label, so category interpretations are generated from actual records. Monetary values are shown in PKR based on the dataset context.
