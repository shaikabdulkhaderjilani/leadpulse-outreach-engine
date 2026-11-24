import csv
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from urllib.parse import quote

import googlemaps
import pandas as pd
import streamlit as st

st.set_page_config(page_title="LeadPulse Outreach Engine", page_icon="🚀", layout="wide")

# --- 1. CONFIGURATIONS FROM st.secrets ---
G_MAPS_API_KEY = st.secrets.get("GOOGLE_MAPS_API_KEY", "")
SENDER_EMAIL = st.secrets.get("SENDER_EMAIL", "")
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "")

# --- 2. LOGGING SETUP ---
LOG_FILE = "campaign_logs.csv"
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Date & Time", "Business Name", "Contact", "Platform", "Status"])


def log_lead(name, contact, platform, status):
    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([timestamp, name, contact, platform, status])


# --- 3. EMAIL FUNCTION ---
def send_email(to_email, biz_name):
    if not SENDER_EMAIL or not APP_PASSWORD:
        return False, "Missing SENDER_EMAIL or APP_PASSWORD in secrets"

    subject = f"Fixing {biz_name}'s Missing Digital Storefront"
    body = (
        f"Hi {biz_name} Team,\n\n"
        f"I was searching for services in your area on Google Maps and noticed something that is quietly costing you money every day: your 'Website' button is completely empty.\n\n"
        f"Here is the brutal truth: When local customers find {biz_name} on Maps but can't click to verify your services, check prices, or book online, 80% of them instantly jump to your competitor's website. You are losing warm, ready-to-pay leads simply because they don't have a place to land.\n\n"
        f"Most traditional agencies will charge you thousands of dollars and take months to fix this. That's where my team is different. We specialize in building premium, high-converting websites exclusively for businesses like yours—at a fraction of the cost, delivered in days.\n\n"
        f"To prove that we are the only clear choice, I didn't just come to pitch. I went ahead and already designed a custom, fully functional website preview specifically for {biz_name}. No strings attached.\n\n"
        f"Reply 'DEMO' to this email, and I'll send the live link right over.\n\n"
        f"Best,\nAbdul"
    )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
        log_lead(biz_name, to_email, "Email", "Sent")
        return True, "Sent"
    except Exception as e:
        log_lead(biz_name, to_email, "Email", f"Failed: {e}")
        return False, str(e)


# --- 4. LEAD DISCOVERY & WHATSAPP LINK GENERATOR ---
def find_leads(search_query: str):
    gmaps = googlemaps.Client(key=G_MAPS_API_KEY)
    places = gmaps.places(query=search_query)
    leads = []

    for place in places.get("results", []):
        place_id = place["place_id"]
        details = gmaps.place(
            place_id=place_id,
            fields=["name", "formatted_phone_number", "website", "formatted_address"],
        ).get("result", {})

        name = details.get("name", "Unknown")
        phone = details.get("formatted_phone_number", "")
        website = details.get("website")
        address = details.get("formatted_address", "")

        if not website and phone:
            phone_fmt = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            if not phone_fmt.startswith("+"):
                phone_fmt = "+91" + phone_fmt

            digits_only = phone_fmt.lstrip("+")
            wa_msg = (
                f"Hi {name} Team!\n\n"
                f"I found your business on Google Maps, but noticed your 'Website' button is completely empty. You are likely losing ready-to-pay clients every day to competitors who have an online storefront.\n\n"
                f"While traditional agencies charge a fortune, we build premium, high-converting websites for businesses like yours at a fraction of the cost.\n\n"
                f"To prove we are the perfect fit, I didn't just come to pitch. I've already designed a custom, fully functional website preview specifically for {name}. No strings attached!\n\n"
                f"Reply 'DEMO' and I'll send the live link right over!\n"
                f"- Abdul"
            )
            wa_link = f"https://wa.me/{digits_only}?text={quote(wa_msg)}"

            leads.append(
                {
                    "Business Name": name,
                    "Phone": phone_fmt,
                    "Address": address,
                    "WhatsApp Link": wa_link,
                }
            )
            log_lead(name, phone_fmt, "WhatsApp Link", "Generated")

    return leads


# --- 5. STREAMLIT UI ---
st.title("LeadPulse Outreach Engine")
st.caption("Discover local businesses without websites on Google Maps & launch instant outreach.")

if "leads" not in st.session_state:
    st.session_state.leads = []

query_input = st.text_input(
    "Target Niche & City",
    placeholder="e.g., Gyms in Hyderabad, Cafes in Dubai, Plumbers in London",
)

if st.button("Find Leads", type="primary"):
    if not G_MAPS_API_KEY:
        st.error("GOOGLE_MAPS_API_KEY missing in Streamlit Secrets.")
    elif not query_input.strip():
        st.warning("Search query enter cheyyi bro.")
    else:
        with st.spinner("Scanning Google Maps for businesses without websites..."):
            try:
                st.session_state.leads = find_leads(query_input.strip())
            except Exception as e:
                st.error(f"Google Maps API Error: {e}")

if st.session_state.leads:
    st.success(f"{len(st.session_state.leads)} target businesses dorikayi (no website listed)!")
    df = pd.DataFrame(st.session_state.leads)

    st.dataframe(
        df,
        column_config={
            "WhatsApp Link": st.column_config.LinkColumn(
                "WhatsApp Pitch",
                display_text="Send WhatsApp",
            )
        },
        use_container_width=True,
        hide_index=True,
    )

    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Leads CSV",
        data=csv_data,
        file_name="leadpulse_targets.csv",
        mime="text/csv",
    )

    st.divider()
    st.subheader("Direct Email Pitch")
    selected_biz = st.selectbox(
        "Select Business",
        options=[lead["Business Name"] for lead in st.session_state.leads],
    )
    target_email = st.text_input("Recipient Email", placeholder="owner@business.com")

    if st.button("Send Email Pitch"):
        if not target_email.strip():
            st.warning("Recipient email enter cheyyi.")
        else:
            ok, status_msg = send_email(target_email.strip(), selected_biz)
            if ok:
                st.success(f"Email sent to {target_email}!")
            else:
                st.error(f"Failed: {status_msg}")