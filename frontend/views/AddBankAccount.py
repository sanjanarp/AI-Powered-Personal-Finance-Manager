import streamlit as st
import requests
from datetime import datetime
from frontend.components.AccountSelector import add_bank_to_state, show_account_selector
import streamlit.components.v1 as components
import pandas as pd
import json


def infer_category(merchant_name: str) -> str:
    """Infer spending category from merchant/transaction name."""
    name = str(merchant_name).lower()
    keyword_map = {
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
        "Transfer": ["transfer", "zelle", "venmo", "paypal", "wire"],
        "Payment": ["payment", "pymnt", "credit card", "autopay"],
        "Deposit": ["deposit", "direct dep", "ach", "gusto", "payroll"],
        "Interest": ["interest", "intrst"],
        "Recreation": ["climbing", "touchstone", "gym", "fitness", "sport"],
    }
    for category, keywords in keyword_map.items():
        if any(kw in name for kw in keywords):
            return category
    return "Uncategorized"

def process_uploaded_statement(uploaded_file):
    if uploaded_file.type != "text/csv":
        return 0

    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Failed to read CSV: {str(e)}")
        return 0

    if "vendor" not in df.columns or "amount ($)" not in df.columns:
        st.error("Missing required columns.")
        return 0

    transactions = []
    for _, row in df.iterrows():
        transaction = {
            "name": row["vendor"],
            "amount": row["amount ($)"]
        }
        # Add category if it exists
        if "category" in df.columns:
            transaction["category"] = row["category"]
        transactions.append(transaction)

    st.session_state["transactions"] = transactions
    return len(transactions)


def add_bank_to_state(institution_name, institution_id, accounts):
    """Helper function to add a bank and its accounts to session state"""
    if 'linked_banks' not in st.session_state:
        st.session_state.linked_banks = {}
    
    # Add or update the bank in session state with the correct structure
    st.session_state.linked_banks[institution_id] = {
        'institution_name': institution_name,  # This is what AccountSelector expects
        'institution_id': institution_id,
        'accounts': accounts
    }
    
    # Initialize selection state for new accounts
    if 'selected_accounts' not in st.session_state:
        st.session_state.selected_accounts = {}
    if institution_id not in st.session_state.selected_accounts:
        st.session_state.selected_accounts[institution_id] = {
            acc['account_id']: False for acc in accounts
        }

def show_add_bank_account():
    st.title("🏦 Connect Your Bank Account")
    
    # Initialize transaction storage if not exists
    if 'all_transactions' not in st.session_state:
        st.session_state.all_transactions = []
    if 'transactions' not in st.session_state:
        st.session_state.transactions = []
    
    # Handle Plaid callback parameters
    status = st.query_params.get("status")
    tokens_str = st.query_params.get("tokens")
    
    # Process tokens if they exist
    if status == "success" and tokens_str:
        try:
            # First try direct JSON parsing
            try:
                tokens = json.loads(tokens_str)
            except json.JSONDecodeError:
                # If direct parsing fails, try URL decoding first
                import urllib.parse
                decoded_tokens = urllib.parse.unquote(tokens_str)
                tokens = json.loads(decoded_tokens)
            
            st.success(f"✅ Successfully linked {len(tokens)} banks!")
            
            # Process all collected tokens
            for token_info in tokens:
                st.info(f"🔄 Processing {token_info['institution_name']}...")
                try:
                    response = requests.post(
                        "http://localhost:5050/api/plaid/exchange_public_token",
                        json=token_info
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        accounts = data.get("accounts", [])
                        
                        # Register the bank and its accounts in session state
                        add_bank_to_state(
                            token_info['institution_name'],
                            token_info['institution_id'],
                            accounts
                        )
                        st.success(f"✅ Successfully processed {token_info['institution_name']}")
                    else:
                        st.error(f"❌ Failed to process {token_info['institution_name']}: {response.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Connection error while processing {token_info['institution_name']}: {str(e)}")
            
            # Clear query parameters and refresh
            st.query_params.clear()
            st.query_params["page"] = "add_bank_account"
            st.rerun()
        
        except Exception as e:
            st.error(f"❌ Error processing tokens: {str(e)}")
            st.error("Token string received:")
            st.code(tokens_str)
            st.error("Please try adding the bank again.")
    elif status == "error":
        error = st.query_params.get("error")
        st.error(f"❌ Error: {error}")
    elif status == "cancelled":
        st.info("ℹ️ Bank linking was cancelled.")
    
    # Create tabs for different methods
    tab1, tab2, tab3 = st.tabs([
        "📊 Manage Connected Banks",
        "➕ Add Another Bank",
        "📄 Upload Bank Statement"
    ])
    
    # Tab 1: Manage Connected Banks
    with tab1:
        st.subheader("Connected Accounts")
        selected_accounts = show_account_selector(show_title=False)
        
        # Transaction Fetching Section
        if selected_accounts:
            st.subheader("📥 Fetch Transactions")
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "Start Date",
                    value=datetime(2025, 1, 1).date(),
                    help="Sandbox data is available from January 2025 to April 2025"
                )
            with col2:
                end_date = st.date_input(
                    "End Date",
                    value=datetime(2025, 4, 30).date(),
                    help="Sandbox data is available from January 2025 to April 2025"
                )

            if st.button("Get Transactions", use_container_width=True):
                st.info(f"📆 Date Range: `{start_date}` to `{end_date}`")
                
                # Fetch transactions for each selected account
                plaid_transactions = []
                with st.spinner("Fetching transactions..."):
                    for account_id in selected_accounts:
                        request_data = {
                            "start_date": str(start_date),
                            "end_date": str(end_date),
                            "account_ids": [account_id]
                        }
                        
                        tx_response = requests.post(
                            "http://localhost:5050/api/plaid/get_transactions",
                            json=request_data
                        )

                        if tx_response.status_code == 200:
                            transactions = tx_response.json().get("transactions", [])
                            # Add source field to distinguish Plaid transactions
                            for tx in transactions:
                                tx["source"] = "plaid"
                            plaid_transactions.extend(transactions)
                        else:
                            st.error(f"Failed to fetch transactions for account {account_id}")

                if plaid_transactions:
                    st.success(f"Found {len(plaid_transactions)} bank transactions.")
                    
                    # Remove any existing Plaid transactions for these accounts
                    st.session_state.all_transactions = [
                        tx for tx in st.session_state.all_transactions 
                        if tx.get("source") != "plaid" or tx.get("account_id") not in selected_accounts
                    ]
                    
                    # Add new Plaid transactions
                    st.session_state.all_transactions.extend(plaid_transactions)
                    
                    # Enrich categories for ALL transactions (single source of truth)
                    for tx in st.session_state.all_transactions:
                        # Negative amounts = refunds/credits — NOT spending
                        amount = float(tx.get("amount", 0))
                        if amount < 0:
                            tx["category"] = "Refund/Credit"
                            continue

                        name_lower = str(tx.get("name", "")).lower()
                        # Check deposit/transfer keywords FIRST (Plaid often miscategorizes these)
                        _deposit_kw = ["deposit", "direct dep", "ach", "payroll", "gusto"]
                        _transfer_kw = ["transfer", "zelle", "venmo", "paypal", "wire"]
                        if any(kw in name_lower for kw in _deposit_kw):
                            tx["category"] = "Deposit"
                        elif any(kw in name_lower for kw in _transfer_kw):
                            tx["category"] = "Transfer"
                        else:
                            # Use infer_category for everything else
                            raw_cat = tx.get("category")
                            if not raw_cat or raw_cat is None or (isinstance(raw_cat, list) and not raw_cat):
                                tx["category"] = infer_category(tx.get("name", ""))
                            elif isinstance(raw_cat, list) and raw_cat:
                                tx["category"] = raw_cat[0] if raw_cat[0] else infer_category(tx.get("name", ""))
                            # If it's already a valid string, keep it

                    # Update the main transactions list
                    st.session_state.transactions = st.session_state.all_transactions.copy()
                    
                    # Build account_id → institution_name map
                    # Build account_id → details map
                    account_info_map = {}
                    if "linked_banks" in st.session_state:
                        for bank in st.session_state["linked_banks"].values():
                            institution = bank.get("institution_name", "Unknown Bank")
                            for account in bank.get("accounts", []):
                                acc_id = account["account_id"]
                                acc_type = account.get("subtype", account.get("type", "Account"))
                                mask = account.get("mask", "XXXX")
                                name = account.get("name", "")
                                account_info_map[acc_id] = {
                                    "institution": institution,
                                    "type": acc_type.title(),
                                    "mask": mask,
                                    "name": name
                                }

                    # Resolve category with same logic as Insights page
                    def resolve_category_for_tx(tx):
                        amount = float(tx.get("amount", 0))
                        if amount < 0:
                            return "Refund/Credit"
                        name_lower = str(tx.get("name", "")).lower()
                        _dep_kw = ["deposit", "direct dep", "ach", "payroll", "gusto"]
                        _xfr_kw = ["transfer", "zelle", "venmo", "paypal", "wire"]
                        if any(kw in name_lower for kw in _dep_kw):
                            return "Deposit"
                        if any(kw in name_lower for kw in _xfr_kw):
                            return "Transfer"
                        cat = tx.get("category")
                        if isinstance(cat, list) and cat:
                            return cat[0] if cat[0] else infer_category(tx.get("name", ""))
                        if isinstance(cat, str) and cat and cat not in ("Uncategorized", "None", "null"):
                            return cat
                        return infer_category(tx.get("name", ""))

                    # Build final table
                    table = [
                        {
                            "Date": pd.to_datetime(tx["date"], errors="coerce").strftime("%Y-%m-%d") if tx.get("date") else "",
                            "Name": tx["name"],
                            "Amount ($)": tx["amount"],
                            "Category": resolve_category_for_tx(tx),
                            "Account": (
                                f"{account_info_map[tx['account_id']]['institution']} – {account_info_map[tx['account_id']]['type']} ({account_info_map[tx['account_id']]['mask']})"
                                if tx.get("account_id") in account_info_map else "Manual Upload – Receipt Transactions"
                            ),
                            "Source": (
                                "📷 Receipt"
                                if tx.get("source") == "manual_upload"
                                else f"🏦 {account_info_map.get(tx.get('account_id'), {}).get('institution', 'Bank')}"
                            )
                        }
                        for tx in st.session_state.transactions
                        if tx.get("account_id") in selected_accounts
                    ]

                    st.dataframe(table, use_container_width=True)
                    
                    
                    # Show total transactions count
                    st.info(f"Total transactions in system: {len(st.session_state.all_transactions)}")
                else:
                    st.warning("No transactions found for the selected period.")
    
    # Tab 2: Add Another Bank
    with tab2:
        st.info("💡 You can connect multiple bank accounts to get a complete view of your finances.")
        if st.button("Link New Bank Account", key="link_new_bank", use_container_width=True):
            js = """
                <script>
                    const redirectUrl = encodeURIComponent('http://localhost:8501/?page=add_bank_account');
                    window.open('http://localhost:5050/launch-plaid-link?redirect_url=' + redirectUrl, '_blank');
                </script>
            """
            st.components.v1.html(js, height=0)
            st.info("✨ Opening bank connection window in a new tab...")
            st.info("👉 Please complete the process in the new tab and return here when done.")
    
    # Tab 3: Upload Bank Statement
    with tab3:
        st.info("📝 Upload your bank statement in CSV format to import transactions.")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a bank statement file",
            type=["csv"],
            help="Currently supporting CSV files. PDF and DOC support coming soon!"
        )
        
        if uploaded_file:
            st.write("File details:")
            file_details = {
                "Filename": uploaded_file.name,
                "File type": uploaded_file.type,
                "File size": f"{uploaded_file.size / 1024:.2f} KB"
            }
            for key, value in file_details.items():
                st.write(f"- {key}: {value}")
            
            if st.button("Process Statement", use_container_width=True):
                with st.spinner("Processing your bank statement..."):
                    num_transactions = process_uploaded_statement(uploaded_file)
                    if num_transactions > 0:
                        st.success(f"✅ Successfully imported {num_transactions} transactions!")
                        
                        # Show the imported transactions
                        if 'transactions' in st.session_state:
                            st.subheader("Imported Transactions")
                            st.dataframe(
                                st.session_state.transactions,
                                use_container_width=True
                            )
                    else:
                        st.error("No transactions were imported. Please check the file format.") 