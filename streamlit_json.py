import streamlit as st
import pandas as pd
import json
import re

# Load JSON file
file_path = "lobbying_data.json"
with open(file_path, "r") as file:
    data = json.load(file)

# Flatten JSON data
df = pd.json_normalize(data, sep="_")

### ---- Helper Functions ---- ###

def extract_lobbyists(activity_list):
    """Extracts unique lobbyists' names and merges covered positions."""
    if isinstance(activity_list, list):
        lobbyist_dict = {}
        for activity in activity_list:
            if "lobbyists" in activity and isinstance(activity["lobbyists"], list):
                for lobbyist in activity["lobbyists"]:
                    name = f"{lobbyist['lobbyist'].get('first_name', '')} {lobbyist['lobbyist'].get('last_name', '')}".strip()
                    covered_position = lobbyist.get("covered_position", "").strip()
                    
                    # Merge lobbyists and covered positions
                    if name:
                        if name not in lobbyist_dict:
                            lobbyist_dict[name] = set()
                        if covered_position and covered_position.lower() not in ["n/a", ""]:
                            lobbyist_dict[name].add(covered_position)

        return [{"name": k, "positions": list(v)} for k, v in lobbyist_dict.items()]
    return []

def extract_foreign_entities(entities_list):
    """Extracts foreign entities' names."""
    if isinstance(entities_list, list):
        return [e["name"] for e in entities_list if "name" in e]
    return []

def normalize_text(text):
    """Normalizes text by converting to lowercase and capitalizing the first letter."""
    return text.lower().capitalize() if isinstance(text, str) else text

def create_hyperlink(url):
    """Creates a clickable hyperlink in Streamlit's dataframe display."""
    if pd.notna(url):
        return f'<a href="{url}" target="_blank">View Filing</a>'
    return ""

### ---- Data Processing ---- ###

# Normalize registrant type (e.g., Law Firm, law firm → Law firm)
df["registrant_type"] = df["registrant_description"].apply(lambda x: normalize_text(x) if pd.notna(x) else "Unknown")

# Extract relevant details
df["foreign_entities"] = df["foreign_entities"].apply(extract_foreign_entities)
df["lobbyists"] = df["lobbying_activities"].apply(extract_lobbyists)

# Format filing year as an integer
df["filing_year"] = df["filing_year"].astype("Int64")

# Add filing document hyperlink
df["filing_link"] = df["filing_document_url"].apply(create_hyperlink)

# Extract cleaned lobbyists and covered positions
df["lobbyist_names"] = df["lobbyists"].apply(lambda x: ", ".join([lobbyist["name"] for lobbyist in x]))
df["covered_positions"] = df["lobbyists"].apply(lambda x: ", ".join(sorted(set([pos for l in x for pos in l["positions"]]))))

# Remove empty covered positions
df["covered_positions"] = df["covered_positions"].replace("", "None")

### ---- Streamlit UI ---- ###

st.title("Lobbying Data Explorer")

# Sidebar Filters
year_filter = st.sidebar.multiselect("Select Year(s)", sorted(df["filing_year"].dropna().unique()))
client_filter = st.sidebar.multiselect("Select Client(s)", sorted(df["client_name"].dropna().unique()))
registrant_filter = st.sidebar.multiselect("Select Registrant(s)", sorted(df["registrant_name"].dropna().unique()))
foreign_filter = st.sidebar.multiselect("Select Foreign Entity", sorted(set([e for sublist in df["foreign_entities"] for e in sublist])))

# Apply filters
df_filtered = df.copy()
if year_filter:
    df_filtered = df_filtered[df_filtered["filing_year"].isin(year_filter)]
if client_filter:
    df_filtered = df_filtered[df_filtered["client_name"].isin(client_filter)]
if registrant_filter:
    df_filtered = df_filtered[df_filtered["registrant_name"].isin(registrant_filter)]
if foreign_filter:
    df_filtered = df_filtered[df_filtered["foreign_entities"].apply(lambda x: any(entity in x for entity in foreign_filter))]

# Select key columns for display
display_columns = [
    "filing_year",
    "filing_type_display",
    "registrant_name",
    "registrant_type",
    "client_name",
    "lobbyist_names",
    "covered_positions",
    "filing_link"
]

# Convert hyperlink column to be clickable in Streamlit
st.subheader("Lobbying Records")
st.markdown(df_filtered[display_columns].to_html(escape=False, index=False), unsafe_allow_html=True)

# Display a Bar Chart of Registrations per Year
st.subheader("Lobbying Registrations Per Year")
st.bar_chart(df_filtered["filing_year"].value_counts())

# Display a Pie Chart of Registrant Types
st.subheader("Types of Registrants")
st.pyplot(df_filtered["registrant_type"].value_counts().plot.pie(autopct='%1.1f%%', figsize=(5, 5)).figure)

# Display Foreign Entities
st.subheader("Foreign Entities Involved")
st.write(df_filtered.explode("foreign_entities")["foreign_entities"].dropna().value_counts())

# Display Unique Covered Positions
st.subheader("Covered Positions of Lobbyists")
st.write(df_filtered["covered_positions"].value_counts())
