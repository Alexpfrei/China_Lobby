import streamlit as st
import pandas as pd
import json

# Load JSON file
file_path = "lobbying_data.json"
with open(file_path, "r") as file:
    data = json.load(file)

# Flatten JSON data
df = pd.json_normalize(data, sep="_")
df["filing_year"] = df["filing_year"].astype(int)




# Handle missing values safely
def extract_lobbyists(activity_list):
    """Extract lobbyists' names safely."""
    if isinstance(activity_list, list):
        return [
            f"{lobbyist['lobbyist'].get('first_name', '')} {lobbyist['lobbyist'].get('last_name', '')}".strip()
            for activity in activity_list if 'lobbyists' in activity and isinstance(activity["lobbyists"], list)
            for lobbyist in activity["lobbyists"]
        ]
    return []

def extract_covered_positions(activity_list):
    """Extract and clean covered positions from lobbyists."""
    if isinstance(activity_list, list):
        positions = [
            str(lobbyist.get("covered_position", "")).strip()  # Convert to string before stripping
            for activity in activity_list if 'lobbyists' in activity and isinstance(activity["lobbyists"], list)
            for lobbyist in activity["lobbyists"]
            if lobbyist.get("covered_position")  # Ensure it's not None
        ]
        # Remove empty strings and "N/A"
        return sorted(set([pos for pos in positions if pos and pos.lower() != "n/a"]))
    return []


df["registrant_type"] = df["registrant_description"].fillna("Unknown")
df["foreign_entities"] = df["foreign_entities"].apply(lambda x: [e["name"] for e in x] if isinstance(x, list) else [])
df["lobbyists"] = df["lobbying_activities"].apply(extract_lobbyists)
df["covered_positions"] = df["lobbying_activities"].apply(extract_covered_positions)

# Convert year to integer to remove comma formatting
df["filing_year"] = df["filing_year"].astype(int)

# Select key columns
columns_to_display = [
    "filing_year",
    "filing_type_display",
    "registrant_name",
    "registrant_type",
    "client_name",
    "lobbyists",
    "covered_positions",
    "foreign_entities",
]

df_filtered = df[columns_to_display]
# Ensure the year column remains an integer when displayed in Streamlit
df_filtered["filing_year"] = df_filtered["filing_year"].astype(int)
# Streamlit UI
st.title("Lobbying Data Explorer")

# Sidebar Filters
year_filter = st.sidebar.multiselect("Select Year(s)", sorted(df_filtered["filing_year"].dropna().unique()))
client_filter = st.sidebar.multiselect("Select Client(s)", sorted(df_filtered["client_name"].dropna().unique()))
registrant_filter = st.sidebar.multiselect("Select Registrant(s)", sorted(df_filtered["registrant_name"].dropna().unique()))
foreign_filter = st.sidebar.multiselect("Select Foreign Entity", sorted(set([e for sublist in df_filtered["foreign_entities"] for e in sublist])))

# Flatten lobbyists for dropdown selection in sidebar
lobbyist_list = sorted(set([lobbyist for sublist in df_filtered["lobbyists"] for lobbyist in sublist]))
lobbyist_filter = st.sidebar.selectbox("Select Lobbyist", [""] + lobbyist_list)

# Apply filters
if year_filter:
    df_filtered = df_filtered[df_filtered["filing_year"].isin(year_filter)]

if client_filter:
    df_filtered = df_filtered[df_filtered["client_name"].isin(client_filter)]

if registrant_filter:
    df_filtered = df_filtered[df_filtered["registrant_name"].isin(registrant_filter)]

if foreign_filter:
    df_filtered = df_filtered[df_filtered["foreign_entities"].apply(lambda x: any(entity in x for entity in foreign_filter))]

if lobbyist_filter:
    df_filtered = df_filtered[df_filtered["lobbyists"].apply(lambda x: lobbyist_filter in x)]

# Display Data
st.dataframe(df_filtered)

# Display a Bar Chart of Registrations per Year
st.subheader("Lobbying Registrations Per Year")
st.bar_chart(df_filtered["filing_year"].value_counts())

# Display Lobbyists' Covered Positions
st.subheader("Covered Positions of Lobbyists")
st.write(df_filtered.explode("covered_positions")["covered_positions"].dropna().value_counts())

# Display Foreign Entities Involved
st.subheader("Foreign Entities Mentioned")
st.write(df_filtered.explode("foreign_entities")["foreign_entities"].dropna().value_counts())

# Show lobbyist details if selected
if lobbyist_filter:
    st.write(f"### Details for {lobbyist_filter}")

    # Get filtered data for the selected lobbyist
    lobbyist_info = df[df["lobbyists"].apply(lambda x: lobbyist_filter in x)]
    
    # Show companies they lobbied for
    st.subheader("Companies Lobbied For")
    st.write(lobbyist_info[["filing_year", "client_name", "registrant_name"]])

    # Show foreign entities they were involved with
    st.subheader("Foreign Entities Involved")
    st.write(lobbyist_info.explode("foreign_entities")["foreign_entities"].dropna().unique())

    # Show covered positions
    st.subheader("Past Covered Positions")
    covered_positions = set([pos for sublist in lobbyist_info["covered_positions"] for pos in sublist])
    if covered_positions:
        st.write(", ".join(covered_positions))
    else:
        st.write("No covered positions found.")
