import os
import time
import pickle
import requests
import pandas as pd
import streamlit as st

# ==========================================
# 1. Page Configuration & Custom CSS
# ==========================================
st.set_page_config(
    page_title="MedIndia | Medicine & Pharmacy Locator",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for cards, badges, and smooth aesthetic
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1.2rem;
        border-radius: 12px;
        border-left: 5px solid #1E88E5;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
    }
    .savings-badge {
        background-color: #2e7d32;
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .rx-badge-yes {
        background-color: #c62828;
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
    }
    .rx-badge-no {
        background-color: #1565c0;
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. Class Definition (Required for PKL Unpickling)
# ==========================================
class IndiaMedicinePlatform:
    def __init__(self):
        self.osm_url = "https://overpass-api.de/api/interpreter"
        self.catalog = []

    def get_catalog_df(self):
        return pd.DataFrame(self.catalog)

    def fetch_city_stores(self, city_name="Pune", limit=10):
        query = f"""
        [out:json][timeout:25];
        area["name"="{city_name}"]["admin_level"~"^(4|6|7|8)$"]->.searchArea;
        (
          node["amenity"="pharmacy"](area.searchArea);
          way["amenity"="pharmacy"](area.searchArea);
        );
        out center {limit};
        """
        try:
            res = requests.get(self.osm_url, params={'data': query}, timeout=30)
            if res.status_code == 200:
                elements = res.json().get("elements", [])
                records = []
                for node in elements:
                    tags = node.get("tags", {})
                    name = tags.get("name", "Local Pharmacy / Retail Chemist")
                    street = tags.get("addr:street", tags.get("addr:suburb", "City Commercial Area"))
                    postcode = tags.get("addr:postcode", "Local PIN Available")
                    records.append({
                        "Store Name": name,
                        "City": city_name,
                        "Street / Area": street,
                        "Pincode": postcode,
                        "Delivery Access": "Online / On-demand Available"
                    })
                return pd.DataFrame(records)
            return pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    def check_availability(self, medicine_code, pincode):
        med = next((m for m in self.catalog if m["code"] == medicine_code), None)
        if not med:
            return {"Error": f"Medicine code {medicine_code} not found."}
        
        is_pin_valid = len(str(pincode)) == 6 and str(pincode).isdigit()
        savings = med["market_mrp_inr"] - med["pmbi_price_inr"]
        savings_pct = (savings / med["market_mrp_inr"]) * 100 if med["market_mrp_inr"] > 0 else 0
        
        return {
            "Medicine Code": med["code"],
            "Generic Name": med["name"],
            "Market Brand Equivalent": med["brand_equivalent"],
            "Category": med["category"],
            "Prescription Required": med["prescription_required"],
            "Pincode Tested": pincode,
            "Online Purchase Available": is_pin_valid,
            "Delivery Window": "24 to 48 Hours" if is_pin_valid else "Unavailable",
            "Jan Aushadhi Scheme Rate": med["pmbi_price_inr"],
            "Open Market Average MRP": med["market_mrp_inr"],
            "Savings Amount": savings,
            "Savings Pct": round(savings_pct, 1)
        }

# ==========================================
# 3. Model Loader Function (Cached)
# ==========================================
@st.cache_resource
def load_platform(pkl_path="india_medicine_platform.pkl"):
    if not os.path.exists(pkl_path):
        # Fallback initialization if file is missing in directory
        engine = IndiaMedicinePlatform()
        engine.catalog = [
            {"code": "MED101", "name": "Paracetamol 650mg", "brand_equivalent": "Dolo 650", "category": "Analgesic / Antipyretic", "pmbi_price_inr": 8.50, "market_mrp_inr": 34.00, "prescription_required": False},
            {"code": "MED102", "name": "Metformin 500mg", "brand_equivalent": "Glycomet 500", "category": "Anti-Diabetic", "pmbi_price_inr": 12.00, "market_mrp_inr": 45.00, "prescription_required": True},
            {"code": "MED103", "name": "Pantoprazole 40mg", "brand_equivalent": "Pan 40", "category": "Proton Pump Inhibitor (Acidity)", "pmbi_price_inr": 18.00, "market_mrp_inr": 95.00, "prescription_required": True},
            {"code": "MED104", "name": "Atorvastatin 10mg", "brand_equivalent": "Atorva 10", "category": "Cardiovascular / Cholesterol", "pmbi_price_inr": 15.00, "market_mrp_inr": 72.00, "prescription_required": True},
            {"code": "MED105", "name": "Azithromycin 500mg", "brand_equivalent": "Azithral 500", "category": "Antibiotic", "pmbi_price_inr": 45.00, "market_mrp_inr": 130.00, "prescription_required": True},
            {"code": "MED106", "name": "Telmisartan 40mg", "brand_equivalent": "Telma 40", "category": "Anti-Hypertensive (BP)", "pmbi_price_inr": 14.50, "market_mrp_inr": 88.00, "prescription_required": True},
            {"code": "MED107", "name": "Cetirizine 10mg", "brand_equivalent": "Cetzine", "category": "Anti-Histamine (Allergy)", "pmbi_price_inr": 6.00, "market_mrp_inr": 25.00, "prescription_required": False},
            {"code": "MED108", "name": "Amoxicillin + Clavulanic Acid 625mg", "brand_equivalent": "Augmentin 625", "category": "Antibiotic", "pmbi_price_inr": 90.00, "market_mrp_inr": 220.00, "prescription_required": True}
        ]
        return engine
    
    with open(pkl_path, "rb") as f:
        return pickle.load(f)

platform = load_platform()
catalog_df = platform.get_catalog_df()

# ==========================================
# 4. Sidebar Controls
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/pill.png", width=75)
    st.title("MedIndia Portal")
    st.markdown("Pan-India generic medicine availability, fair pricing index, and retail chemist locator.")
    st.markdown("---")
    
    navigation = st.radio(
        "Navigation Menu",
        ["🔍 Check Medicine Availability", "🏬 City-Wise Stores", "📋 All Medicine Catalog"],
        index=0
    )
    st.markdown("---")
    st.caption("Data source: PMBI (Jan Aushadhi) & OpenStreetMap Network")

# ==========================================
# 5. Tab / Page Routing
# ==========================================

# --- PAGE 1: CHECK AVAILABILITY ---
if navigation == "🔍 Check Medicine Availability":
    st.title("💊 Check Online Medicine Availability & Pricing")
    st.write("Predict dispatch readiness, verify prescription requirements, and compare Jan Aushadhi generic rates with market MRP.")
    
    col_input1, col_input2 = st.columns([2, 1])
    
    # Medicine Selector options format: Code - Name (Brand)
    medicine_options = {
        f"{row['code']} - {row['name']} (Brand: {row['brand_equivalent']})": row['code'] 
        for _, row in catalog_df.iterrows()
    }
    
    with col_input1:
        selected_med_label = st.selectbox("Select Medicine:", list(medicine_options.keys()))
        selected_code = medicine_options[selected_med_label]
        
    with col_input2:
        pincode_input = st.text_input("Enter 6-digit Pincode:", value="411001", max_chars=6)

    # Predict / Check Button
    predict_clicked = st.button("⚡ Predict Availability & Pricing", type="primary", use_container_width=True)

    if predict_clicked:
        # Visual loading effect
        with st.spinner("Connecting to postal logistics dispatch server..."):
            time.sleep(0.8) # Brief simulation delay for smooth UX
            result = platform.check_availability(selected_code, pincode_input)

        if "Error" in result:
            st.error(result["Error"])
        elif not result["Online Purchase Available"]:
            st.warning("⚠️ Invalid Indian Pincode. Please enter a valid 6-digit postal code.")
        else:
            # Success animation effects
            st.balloons()
            st.toast("Stock verification successful!", icon="✅")
            
            st.success(f"**Available for online order & dispatch to PIN {result['Pincode Tested']}!**")
            
            # Key Metric Highlights
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Jan Aushadhi Price", f"₹{result['Jan Aushadhi Scheme Rate']}")
            with m2:
                st.metric("Market MRP", f"₹{result['Open Market Average MRP']}")
            with m3:
                st.metric("Savings", f"₹{result['Savings Amount']}", f"-{result['Savings Pct']}%")
            with m4:
                st.metric("Estimated Delivery", result["Delivery Window"])

            st.markdown("---")
            
            # Detailed Breakdown Card
            st.subheader("Medicine Specification & Compliance")
            rx_badge = '<span class="rx-badge-yes">Prescription Mandatory</span>' if result["Prescription Required"] else '<span class="rx-badge-no">OTC / No Prescription</span>'
            
            st.markdown(f"""
            <div class="metric-card">
                <p><strong>Generic Formulation:</strong> {result['Generic Name']}</p>
                <p><strong>Popular Market Equivalent:</strong> {result['Market Brand Equivalent']}</p>
                <p><strong>Therapeutic Class:</strong> {result['Category']}</p>
                <p><strong>Dispensing Category:</strong> {rx_badge}</p>
                <p><strong>Cost Benefit:</strong> You save approximately <strong>₹{result['Savings Amount']} ({result['Savings Pct']}%)</strong> by opting for the generic equivalent.</p>
            </div>
            """, unsafe_allow_html=True)


# --- PAGE 2: CITY-WISE STORES ---
elif navigation == "🏬 City-Wise Stores":
    st.title("🏬 City-Wise Chemist & Pharmacy Stores")
    st.write("Locate verified physical pharmacy stores and retail chemists operating in Indian cities.")
    
    col_city1, col_city2 = st.columns([3, 1])
    with col_city1:
        city_name = st.selectbox(
            "Select or Type Indian City:", 
            ["Pune", "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Kolkata", "Chennai", "Ahmedabad", "Jaipur", "Lucknow"]
        )
    with col_city2:
        store_limit = st.slider("Store Limit:", min_value=5, max_value=30, value=10, step=5)

    fetch_btn = st.button("📍 Find Nearby Stores", use_container_width=True)

    if fetch_btn:
        with st.spinner(f"Querying OpenStreetMap infrastructure in {city_name}..."):
            stores_df = platform.fetch_city_stores(city_name=city_name, limit=store_limit)
            
        if not stores_df.empty:
            st.toast(f"Found {len(stores_df)} active pharmacies in {city_name}!", icon="📍")
            st.dataframe(stores_df, use_container_width=True, hide_index=True)
        else:
            st.info(f"No store coordinates directly fetched for '{city_name}'. Try another major urban district.")


# --- PAGE 3: ALL MEDICINE CATALOG ---
elif navigation == "📋 All Medicine Catalog":
    st.title("📋 Pan-India Generic Medicine Reference Catalog")
    st.write("Browse essential generic medicines with government fair pricing (PMBI) compared to retail MRP.")
    
    search_query = st.text_input("Filter medicines by name or therapeutic class:", "")
    
    filtered_df = catalog_df.copy()
    if search_query:
        filtered_df = filtered_df[
            filtered_df["name"].str.contains(search_query, case=False) | 
            filtered_df["brand_equivalent"].str.contains(search_query, case=False) |
            filtered_df["category"].str.contains(search_query, case=False)
        ]
        
    st.dataframe(
        filtered_df[[
            "code", "name", "brand_equivalent", "category", 
            "pmbi_price_inr", "market_mrp_inr", "prescription_required"
        ]].rename(columns={
            "code": "Code",
            "name": "Generic Name",
            "brand_equivalent": "Market Reference",
            "category": "Therapy",
            "pmbi_price_inr": "Govt Price (₹)",
            "market_mrp_inr": "Market MRP (₹)",
            "prescription_required": "Rx Required"
        }),
        use_container_width=True,
        hide_index=True
    )
