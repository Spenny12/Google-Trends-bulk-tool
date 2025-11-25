import streamlit as st
import pandas as pd
from pytrends.request import TrendReq
from io import StringIO, BytesIO
from datetime import datetime

# --- Configuration ---
# Initialize the PyTrends request object
pytrends = TrendReq(hl='en-US', tz=360) # hl='en-US' for English, tz=360 for GMT-6 (Central US Time)

# --- Function to format the timeframe string ---
def get_timeframe_string(months):
    """Converts the number of months into a PyTrends-compatible timeframe string."""
    today = datetime.now()
    if months == 12:
        # Last 12 months is 'today N months ago'
        return 'today 12-m'
    elif months == 24:
        # Last 24 months is 'today 24-m'
        return 'today 24-m'
    else:
        # Default to 12 months if an unexpected value is passed
        return 'today 12-m'

# --- Function to fetch Google Trends data ---
@st.cache_data
def fetch_trends_data(queries, months):
    """
    Fetches interest over time data for a list of queries.
    Google Trends API limits to 5 queries per request.
    """
    st.info(f"Fetching data for {len(queries)} queries over the last {months} months...")

    # Split the list of all queries into chunks of 5
    chunk_size = 5
    query_chunks = [queries[i:i + chunk_size] for i in range(0, len(queries), chunk_size)]
    
    all_data = []
    
    timeframe = get_timeframe_string(months)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, chunk in enumerate(query_chunks):
        try:
            # Update progress
            progress = (i + 1) / len(query_chunks)
            progress_bar.progress(progress)
            status_text.text(f"Processing chunk {i + 1} of {len(query_chunks)}: {', '.join(chunk)}")
            
            # Build the payload for PyTrends
            pytrends.build_payload(kw_list=chunk, cat=0, timeframe=timeframe, geo='', gprop='')
            
            # Request the data
            data = pytrends.interest_over_time()
            
            # Remove the 'isPartial' column which is not needed for the final output
            if 'isPartial' in data.columns:
                data = data.drop(columns=['isPartial'])
            
            all_data.append(data)
            
        except Exception as e:
            st.error(f"An error occurred while fetching data for the chunk {chunk}: {e}")
            continue

    progress_bar.empty()
    status_text.empty()
    
    if all_data:
        # Concatenate all DataFrames side-by-side (index is Date)
        final_df = pd.concat(all_data, axis=1)
        # Remove duplicate columns if any (shouldn't happen, but good practice)
        final_df = final_df.loc[:, ~final_df.columns.duplicated()]
        return final_df
    else:
        return None

# --- Main Streamlit App Logic ---
def main():
    st.set_page_config(
        page_title="Bulk Google Trends Data Fetcher",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("📈 Bulk Google Trends Data Fetcher")
    st.markdown("""
        Upload a **CSV file** containing your search queries (one query per row/cell in the first column). 
        The tool will use `pytrends` to fetch the **Interest Over Time** data for each query.
        *(Note: Google Trends API only allows 5 queries per batch.)*
    """)
    
    st.markdown("---")

    # --- Sidebar for User Input ---
    with st.sidebar:
        st.header("Settings")
        
        # 1. Date Range Selection
        time_range = st.radio(
            "Select Time Range:",
            [12, 24],
            format_func=lambda x: f"Last {x} Months",
            index=0
        )
        
        # 2. File Uploader
        uploaded_file = st.file_uploader(
            "Upload your CSV file", 
            type="csv",
            help="The CSV must contain your queries in the *first column*."
        )

        st.markdown("---")
        st.subheader("Output Format")
        st.markdown("The output will be a single CSV where:")
        st.markdown("* The first column is the **Date/Week**.")
        st.markdown("* Subsequent columns are the **Interest Scores** for each query.")

    # --- Main Content Area ---
    if uploaded_file is not None:
        try:
            # Read the uploaded CSV file
            data = pd.read_csv(uploaded_file, header=None)
            
            # Assuming the queries are in the first column (index 0)
            # Drop any rows where the query is missing/NaN and convert to a list of strings
            queries = data.iloc[:, 0].dropna().astype(str).str.strip().tolist()
            
            if not queries:
                st.error("The CSV file is empty or does not contain any queries in the first column.")
                return

            st.success(f"Successfully loaded **{len(queries)}** queries.")
            
            # Display a preview of the queries
            with st.expander("Preview of Queries"):
                st.dataframe(pd.DataFrame({"Query": queries}))
            
            # Fetch button
            if st.button("Start Fetching Google Trends Data"):
                st.subheader(f"Results for Last {time_range} Months")
                
                # Fetch data
                final_df = fetch_trends_data(queries, time_range)
                
                if final_df is not None:
                    st.success("✅ Data fetching complete!")
                    
                    st.dataframe(final_df)
                    
                    # --- Data Download Section ---
                    st.markdown("### Download Data")
                    
                    # Convert DataFrame to CSV in memory
                    csv_data = final_df.to_csv().encode('utf-8')
                    
                    # Create a unique filename
                    filename = f"google_trends_data_{time_range}months_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    
                    st.download_button(
                        label="⬇️ Download All Trends Data as CSV",
                        data=csv_data,
                        file_name=filename,
                        mime='text/csv',
                    )
                else:
                    st.warning("No data could be fetched. Please check the queries and try again.")
        
        except Exception as e:
            st.error(f"An error occurred during file processing or data fetching: {e}")
            st.warning("Please ensure your CSV is correctly formatted with queries in the first column.")

    else:
        st.info("Waiting for a CSV file upload. Please configure the settings in the sidebar.")
        st.markdown("""
        ### Example CSV Format
        | Column 1 | (Other Columns Ignored) |
        |---|---|
        | pizza recipe | ... |
        | data science course | ... |
        | AI tools | ... |
        """)

if __name__ == '__main__':
    main()
