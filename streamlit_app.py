import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import requests
import time
import datetime
import calendar

# Constants
API_BASE = "https://li.quest/v1/analytics/transfers"
INTEGRATOR = "jumper.exchange"

def fetch_transactions(wallet_address):
    """
    Fetch transactions from the API for a given wallet address.
    Returns a list of transactions and a dictionary of activity days.
    """
    # Get timestamp from one year ago
    one_year_ago_timestamp = int(time.time()) - 365 * 24 * 60 * 60
    api_url = f"{API_BASE}?integrator={INTEGRATOR}&wallet={wallet_address}&fromTimestamp={one_year_ago_timestamp}"

    # Fetch data
    response = requests.get(api_url)
    data = response.json()
    transactions = data.get("transfers", [])

    # Extract activity days
    activity_days = {}
    for tx in transactions:
        timestamp = tx["receiving"]["timestamp"]
        date = datetime.datetime.utcfromtimestamp(timestamp).date()
        activity_days[date] = activity_days.get(date, 0) + 1

    return transactions, activity_days

def calculate_streaks(activity_days):
    """
    Calculate the current active streak and longest streak from activity days.
    """
    dates = sorted(activity_days.keys())
    longest_streak = 0
    current_streak = 0
    max_streak = 0
    previous_date = None

    for date in dates:
        if previous_date and (date - previous_date).days == 1:
            current_streak += 1
        else:
            current_streak = 1  # Reset streak if there's a gap

        max_streak = max(max_streak, current_streak)
        previous_date = date

    # Check if the current streak is ongoing
    today = datetime.date.today()
    active_streak = current_streak if dates and today == dates[-1] else 0

    return active_streak, max_streak

def calculate_chain_and_amount(transactions):
    """
    Calculate the number of distinct receiving chainIds and total transaction amount in USD.
    """
    receiving_chain_ids = {tx["receiving"]["chainId"] for tx in transactions}
    num_distinct_chain_ids = len(receiving_chain_ids)
    total_amount_usd = sum(float(tx["receiving"]["amountUSD"]) for tx in transactions)

    return num_distinct_chain_ids, total_amount_usd

def generate_contribution_data(activity_days):
    """
    Generate data for a GitHub-style contribution graph.
    Returns a 2D numpy array formatted for heatmap visualization.
    """
    if not activity_days:
        return np.array([])

    dates = sorted(activity_days.keys())
    start_date = min(dates)
    end_date = datetime.date.today()

    # Create a daily activity array
    num_days = (end_date - start_date).days + 1
    heatmap_data = np.zeros(num_days)

    for i in range(num_days):
        date = start_date + datetime.timedelta(days=i)
        heatmap_data[i] = activity_days.get(date, 0)

    # Reshape into weeks (7-day rows)
    start_weekday = start_date.weekday()  # Monday = 0, Sunday = 6
    num_weeks = (num_days + start_weekday) // 7 + 1
    padded_data = np.pad(heatmap_data, (start_weekday, num_weeks * 7 - (num_days + start_weekday)), 'constant')

    heatmap_data = padded_data.reshape((num_weeks, 7)).T  # Transpose for correct orientation

    return heatmap_data, start_date, end_date

def analyze_wallet_activity(wallet_address):
    transactions, activity_days = fetch_transactions(wallet_address)
    active_streak, longest_streak = calculate_streaks(activity_days)
    num_distinct_chain_ids, total_amount_usd = calculate_chain_and_amount(transactions)
    heatmap_data, start_date, end_date = generate_contribution_data(activity_days)

    return {
        "num_distinct_chain_ids": num_distinct_chain_ids,
        "total_amount_usd": total_amount_usd,
        "active_streak": active_streak,
        "longest_streak": longest_streak,
        "heatmap_data": heatmap_data,
        "start_date": start_date,
        "end_date": end_date
    }


###############
# Streamlit UI
###############
st.set_page_config(page_title="Jumper Wallet Activity", layout="wide")

st.title("Your Last 365d Activity on Jumper")

wallet_address = st.text_input("Enter your wallet address:", "")

if wallet_address:
    result = analyze_wallet_activity(wallet_address)
    
    st.subheader("Your Activity Summary")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Streak", result['active_streak'])
    col2.metric("Longest Streak", result['longest_streak'])
    col3.metric("Distinct Chains Visited", result['num_distinct_chain_ids'])
    col4.metric("Total Volume (USD)", f"${result['total_amount_usd']:,.2f}")
    
    # Heatmap Contribution Graph
    st.subheader("Your Jumper Contribution Graph")
    heatmap_data = result['heatmap_data']
    start_date = result['start_date']
    end_date = result['end_date']

    if heatmap_data is not None:
        # Generate Month Labels
        num_weeks = heatmap_data.shape[1]
        date_labels = [start_date + datetime.timedelta(weeks=i) for i in range(num_weeks)]
        month_labels = [calendar.month_abbr[d.month] if d.day <= 7 else '' for d in date_labels]

        # Plot the contribution graph
        fig, ax = plt.subplots(figsize=(12, 4))
        sns.heatmap(
            heatmap_data, cmap="Greens", linewidths=0.5, linecolor="gray",
            cbar=False, square=True, ax=ax
        )

        # Add x-axis labels (Months)
        ax.set_xticks(np.arange(len(month_labels)) + 0.5)
        ax.set_xticklabels(month_labels, rotation=45, ha="center", fontsize=10)

        # Add y-axis labels (Days of Week)
        ax.set_yticks(np.arange(7) + 0.5)
        ax.set_yticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], rotation=0, fontsize=10)

        ax.set_title("Contribution Graph")

        st.pyplot(fig)
        
        st.markdown("\* Darker squares indicate more activity on that day.")