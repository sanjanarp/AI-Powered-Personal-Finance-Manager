# frontend/app.py
import streamlit as st
import sys
import os
from pathlib import Path
from frontend.views.AddBankAccount import show_add_bank_account
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Add project root to Python path first
# Add both frontend and project root to Python path
frontend_path = Path(__file__).parent
project_root = frontend_path.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Set page config
st.set_page_config(
    page_title="AI Finance Manager",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "current_page" not in st.session_state:
    st.session_state["current_page"] = st.query_params.get("page", "home")

# Custom CSS
st.markdown("""
    <style>
        section[data-testid="stSidebar"] > div {
            background-color: #0f172a;
            padding: 1.5rem 1rem;
        }
        .sidebar-logo {
            display: flex;
            align-items: center;
            gap: 0.875rem;
            margin-bottom: 2.5rem;
            padding: 0 0.5rem;
        }
        .logo-icon {
            width: 2.25rem;
            height: 2.25rem;
            background-color: #1e293b;
            border-radius: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
        }
        .company-name {
            color: #f8fafc;
            font-size: 1.125rem;
            font-weight: 500;
        }
        .nav-button {
            width: 100%;
            color: #e2e8f0;
            border: none;
            text-align: left;
            padding: 0.625rem 0.875rem;
            margin: 0.125rem 0;
            border-radius: 0.375rem;
            cursor: pointer;
            font-size: 0.9375rem;
            transition: background-color 0.15s ease;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            background-color: transparent;
            font-weight: 400;
            line-height: 1.5;
        }
        .nav-button:hover {
            background-color: rgba(148, 163, 184, 0.1);
        }
        .nav-selected {
            background-color: #334155 !important;
            color: #ffffff;
        }
        .nav-wrapper {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
            padding: 0 0.25rem;
        }
        .nav-button:focus {
            outline: none;
            box-shadow: none;
        }
        #MainMenu, footer, header {visibility: hidden;}
        section[data-testid="stSidebar"] .block-container {
            padding: 0;
        }
        /* Fix button width consistency */
        .stButton > button {
            width: 100% !important;
        }
        /* Ensure icons are consistently sized */
        .nav-button span {
            font-size: 1.125rem;
            min-width: 1.5rem;
            text-align: center;
        }
        /* Auto-scroll behavior */
        div.element-container:first-of-type {
            scroll-margin-top: 0;
        }
        
        /* Smooth scrolling */
        .main {
            scroll-behavior: smooth;
        }
    </style>
    <script>
        // More robust scroll to top function
        function scrollToTop() {
            setTimeout(function() {
                window.parent.document.querySelector('section.main').scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
            }, 100);
        }
        
        // Call on page load
        window.addEventListener('load', scrollToTop);
        
        // Also call when Streamlit has finished re-running
        window.addEventListener('streamlit:render', scrollToTop);
    </script>
""", unsafe_allow_html=True)

# Logo and App Title
st.sidebar.markdown("""
    <div class="sidebar-logo">
        <div class="logo-icon">💰</div>
        <div class="company-name">FinanceAI</div>
    </div>
""", unsafe_allow_html=True)

# Navigation
pages = [
    ("🏠", "Home", "home"),
    ("🏦", "Add Bank Account", "add_bank"),
    ("📈", "Spending Insights", "insights"),
    ("📊", "Budget Tracking", "budget"),
    ("🔔", "Bill Reminders", "bills"),
    ("💬", "AI Financial Advisor", "chatbot"),
    ("📸", "Receipt Parser", "receiptparser")
]

st.sidebar.markdown('<div class="nav-wrapper">', unsafe_allow_html=True)
for icon, label, page in pages:
    selected = "nav-button nav-selected" if st.session_state["current_page"] == page else "nav-button"
    if st.sidebar.button(f"{icon} {label}", key=page):
        st.session_state["current_page"] = page
        # Update URL when clicking navigation
        st.query_params["page"] = page
        st.rerun()
    st.sidebar.markdown(f"""
        <script>
        var btn = window.parent.document.querySelector('button[key="nav_{page}"]');
        if (btn) {{
            btn.className = '{selected}';
        }}
        </script>
    """, unsafe_allow_html=True)
st.sidebar.markdown('</div>', unsafe_allow_html=True)

# Import views
from frontend.views.Home import show_home
from frontend.views.BudgetTracker import show_budget_tracker
from frontend.views.Insights import show_insights
from frontend.views.BillReminders import show_bill_reminders
from frontend.views.Chatbot import show_chatbot

# Handle Plaid callback status
status = st.query_params.get("status")
institution_name = st.query_params.get("institution_name")
error = st.query_params.get("error")

if status:
    if status == "success":
        # Update current page to add_bank
        st.session_state["current_page"] = "add_bank"
    elif status == "error" and error:
        st.error(f"❌ Error: {error}")
        st.session_state["current_page"] = "add_bank"
    elif status == "cancelled":
        st.info("ℹ️ Bank linking was cancelled.")
        st.session_state["current_page"] = "add_bank"

# ──────────────────────────────────────────────────────────────────────────────
# CENTRALIZED CATEGORY ENRICHMENT — runs on every rerun, before any page loads.
# This is the single source of truth for transaction categories.
# ──────────────────────────────────────────────────────────────────────────────
def _enrich_session_transactions():
    """Fix categories on ALL transactions in session_state, in-place."""
    tx_lists = []
    if "transactions" in st.session_state:
        tx_lists.append(st.session_state["transactions"])
    if "all_transactions" in st.session_state:
        tx_lists.append(st.session_state["all_transactions"])
        
    if not tx_lists:
        return

    _dep_kw = ["deposit", "direct dep", "ach", "payroll", "gusto"]
    _xfr_kw = ["transfer", "zelle", "venmo", "paypal", "wire"]
    _kw_map = {
        "Food & Drink": ["starbucks", "mcdonald", "dunkin", "chipotle", "pizza", "burger",
                         "taco", "wendy", "chick-fil", "subway", "panera", "grubhub",
                         "doordash", "uber eats", "postmates", "restaurant", "cafe", "diner",
                         "bakery", "coffee"],
        "Transportation": ["uber", "lyft", "gas", "shell", "chevron", "exxon", "bp ",
                           "parking", "transit", "metro", "amtrak", "fuel"],
        "Travel": ["airline", "united air", "delta air", "american air", "southwest",
                   "jetblue", "hotel", "marriott", "hilton", "airbnb", "booking", "expedia"],
        "Shopping": ["amazon", "walmart", "target", "costco", "best buy", "ebay",
                     "etsy", "ikea", "home depot", "lowe", "sparkfun"],
        "Entertainment": ["netflix", "spotify", "hulu", "disney", "apple music",
                          "youtube", "gaming", "cinema", "movie", "theater"],
        "Bills & Utilities": ["electric", "water", "internet", "comcast", "verizon",
                              "at&t", "t-mobile", "utility", "power", "gas bill"],
        "Healthcare": ["pharmacy", "cvs", "walgreens", "doctor", "hospital", "dental",
                       "medical", "health"],
        "Groceries": ["grocery", "trader joe", "whole foods", "safeway", "kroger",
                      "publix", "aldi", "sprouts"],
        "Payment": ["payment", "pymnt", "credit card", "autopay"],
        "Interest": ["interest", "intrst"],
        "Recreation": ["climbing", "touchstone", "gym", "fitness", "sport"],
    }

    for txs in tx_lists:
        for tx in txs:
            try:
                amount = float(tx.get("amount", 0))
            except (ValueError, TypeError):
                amount = 0
            name_lower = str(tx.get("name", "")).lower()

            # Priority 1: negative amounts are refunds/credits
            if amount < 0:
                tx["category"] = "Refund/Credit"
                continue
            # Priority 2: deposit keywords in name
            if any(kw in name_lower for kw in _dep_kw):
                tx["category"] = "Deposit"
                continue
            # Priority 3: transfer keywords in name
            if any(kw in name_lower for kw in _xfr_kw):
                tx["category"] = "Transfer"
                continue
            # Priority 4: existing valid category string
            cat = tx.get("category")
            if isinstance(cat, list) and cat:
                tx["category"] = cat[0] if cat[0] else None
                cat = tx["category"]
            if isinstance(cat, str) and cat and cat not in ("Uncategorized", "None", "null", ""):
                continue
            # Priority 5: infer from merchant name
            matched = "Uncategorized"
            for cat_name, keywords in _kw_map.items():
                if any(kw in name_lower for kw in keywords):
                    matched = cat_name
                    break
            tx["category"] = matched

_enrich_session_transactions()

# Page rendering based on session state
# Lazy loading: only import the view when needed
if st.session_state["current_page"] == "home":
    from frontend.views.Home import show_home
    show_home()
elif st.session_state["current_page"] == "add_bank":
    from views.AddBankAccount import show_add_bank_account
    show_add_bank_account()
elif st.session_state["current_page"] == "budget":
    from views.BudgetTracker import show_budget_tracker
    show_budget_tracker()
elif st.session_state["current_page"] == "insights":
    from views.Insights import show_insights
    show_insights()
elif st.session_state["current_page"] == "bills":
    from views.BillReminders import show_bill_reminders
    show_bill_reminders()
elif st.session_state["current_page"] == "chatbot":
    from views.Chatbot import show_chatbot
    show_chatbot()
elif st.session_state["current_page"] == "receiptparser":
    from views.ReceiptParser import show_receipt_parser
    show_receipt_parser()