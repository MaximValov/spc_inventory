# streamlit_app.py
import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

# Configure file storage
UPLOAD_DIR = r"C:/work/python/inventory/specimen_uploads/"
os.makedirs(UPLOAD_DIR, exist_ok=True)
st.set_page_config(page_title="Specimens Database", page_icon="🔬", layout="wide")


def get_specimen_files(specimen_id):
    """Get all files for a specimen"""
    conn = sqlite3.connect('specimens2.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, file_type, file_path, original_filename, upload_time 
        FROM specimen_files 
        WHERE specimen_id = ? 
        ORDER BY upload_time DESC
    ''', (specimen_id,))

    files = cursor.fetchall()
    conn.close()
    return files


def get_specimen_info(specimen_id):
    """Get test_name and dogovor for a specimen"""
    conn = sqlite3.connect('specimens2.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT test_name, dogovor FROM specimens_table WHERE id = ?
    ''', (specimen_id,))

    result = cursor.fetchone()
    conn.close()
    return result if result else ("unknown", "unknown")
def get_all_specimens():
    """Fetch all specimens from database"""
    conn = sqlite3.connect('specimens2.db')
    df = pd.read_sql_query("SELECT * FROM specimens_table ORDER BY id", conn)
    conn.close()
    return df

def create_connection():
    """Create a database connection to the SQLite database"""
    conn = None
    try:
        conn = sqlite3.connect('specimens2.db', check_same_thread=False)
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
    return conn

def save_edited_specimens_simple(edited_df, original_df):
    """Simple approach using the returned dataframe"""
    conn = create_connection()
    if conn is None:
        st.error("Database connection failed")
        return

    cursor = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Get all column names from the DataFrame (except 'id' for new rows)
    all_columns = [col for col in edited_df.columns if col != 'id']

    # Build the dynamic INSERT statement
    placeholders = ', '.join(['?'] * len(all_columns))
    column_names = ', '.join(all_columns)
    try:
        # Compare original vs edited to find changes
        for index, row in edited_df.iterrows():
            if index < len(original_df):
                # Existing row - check if it changed
                original_row = original_df.iloc[index]
                if not row.equals(original_row):
                    cursor.execute('''
                        UPDATE specimens_table 
                        SET status = ?, test_name = ?, notes=? ,dogovor=? ,location=? ,amount=? ,status_update_time = ?
                        WHERE id = ?
                    ''', (row['status'], row['test_name'],row['notes'],row['dogovor'],row['location'],row['amount'], current_time, row['id']))
                    st.write(f"Updated specimen {row['id']}")
            else:
                # New row
                values = [row[col] for col in all_columns] + [row['id']]
                cursor.execute('''
                                    INSERT INTO specimens_table (status, test_name,amount, status_update_time) 
                                    VALUES (?, ?, ?,?)
                                ''', (row['status'], row['test_name'], row['amount'],current_time))
                st.write(f"Added new specimen")

        conn.commit()
        st.success("✅ Database updated successfully!")

    except Exception as e:
        conn.rollback()
        st.error(f"❌ Error: {str(e)}")
    finally:
        conn.close()
def update_specimen_file(specimen_id, file_path, original_filename, file_type):
    """Update a specimen's file path in the specimen_files table"""
    conn = sqlite3.connect('specimens2.db')
    cursor = conn.cursor()

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """INSERT INTO specimen_files 
        (specimen_id, file_type, file_path, original_filename, upload_time) 
        VALUES (?, ?, ?, ?, ?)""",
        (specimen_id, file_type, file_path, original_filename, current_time)
    )
    conn.commit()
    conn.close()

def update_specimen_pdf(specimen_id, pdf_filename):
    """Update a specimen's PDF path in the database"""
    conn = sqlite3.connect('specimens2.db')
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE specimens_table SET pdf_path = ? WHERE id = ?",
        (pdf_filename, specimen_id)
    )
    conn.commit()
    conn.close()


def handle_file_upload(specimen_id, uploaded_file, test_name, dogovor):
    """Handle file upload and save file path to database"""
    if uploaded_file is not None:
        # Create filename using the new convention
        original_name = os.path.splitext(uploaded_file.name)[0]
        file_extension = os.path.splitext(uploaded_file.name)[1]
        filename = f"{test_name}_{dogovor}_{original_name}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        # Save the file
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Determine file type
        file_type = 'photo' if uploaded_file.type.startswith('image/') else 'document'

        # Save file info to database
        update_specimen_file(specimen_id, file_path, uploaded_file.name, file_type)
        return True
    return False

def display_specimen_with_local_files(row, upload_dir):
    """Display specimen information with multiple files"""

    # Get all files for this specimen
    files = get_specimen_files(row['id'])
    photo_files = [f for f in files if f[1] == 'photo']  # file_type = 'photo'
    document_files = [f for f in files if f[1] == 'document']  # file_type = 'document'

    with st.container():
        col1, col2 = st.columns([1, 3])

        with col1:
            # Display all photos
            if photo_files:
                st.write("**Photos:**")
                for file_id, file_type, file_path, original_filename, upload_time in photo_files:
                    if os.path.exists(file_path):
                        st.image(file_path, width=150, caption=original_filename)
                    else:
                        pass
                        # st.write(f"❌ Missing: {original_filename}")
            else:
                st.write("No photos available")

        with col2:
            # Specimen info
            st.write(f"<p style='color: black; font-size: 8px;'><b>Specimen ID {row['id']}</b></p>",
                     unsafe_allow_html=True)
            st.write(f"<p style='color: darkblue; font-size: 16px;'><b>Test:</b> {row['test_name']}</p>",
                     unsafe_allow_html=True)

            # Document files section
            if document_files:
                st.write("**Documents:**")
                for file_id, file_type, file_path, original_filename, upload_time in document_files:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as doc_file:
                            st.download_button(
                                label=f"📄 {original_filename}",
                                data=doc_file,
                                file_name=original_filename,
                                key=f"doc_{file_id}"
                            )
                    else:
                        pass
                        # st.write(f"❌ Missing: {original_filename}")
            else:
                st.write("No documents available")

        st.divider()


def handle_pdf_upload(specimen_id, uploaded_file):
    """Handle PDF upload and save file path to database"""
    if uploaded_file is not None:
        # Create a unique filename
        file_extension = ".pdf"
        filename = f"specimen_{specimen_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        print('pdff', file_path)
        # Save the file
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Save file path to database
        conn = sqlite3.connect('specimens2.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO specimen_files (specimen_id, file_type, file_path)
            VALUES (?, ?, ?)
        ''', (specimen_id, 'pdf', file_path))
        conn.commit()
        conn.close()

        return True
    return False


def save_edited_specimens_with_deletion(edited_df, original_df, editor_state):
    """Save edits, new rows, and handle deletions"""
    conn = create_connection()
    cursor = conn.cursor()

    try:
        # Handle deleted rows:cite[3]
        if 'deleted_rows' in editor_state:
            for row_index in editor_state['deleted_rows']:
                # Get the actual ID from the original dataframe
                specimen_id = original_df.iloc[row_index]['id']
                cursor.execute('DELETE FROM specimens_table WHERE id = ?', (specimen_id,))

        # Process edits and new rows (your existing logic)
        for index, row in edited_df.iterrows():
            if pd.isna(row['id']) or row['id'] == 0:
                # INSERT new specimen
                cursor.execute('''
                    INSERT INTO specimens_table (status, test_name, notes, status_update_time) 
                    VALUES (?, ?, ?, ?)
                ''', (row['status'], row['test_name'], row.get('notes', ''),
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            else:
                # UPDATE existing specimen
                cursor.execute('''
                    UPDATE specimens_table 
                    SET status = ?, test_name = ?, notes = ?, status_update_time = ?
                    WHERE id = ?
                ''', (row['status'], row['test_name'], row.get('notes', ''),
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row['id']))

        conn.commit()

    except Exception as e:
        conn.rollback()
        st.error(f"Error saving changes: {e}")
    finally:
        conn.close()


def main():
    st.title("🔬 Specimens Database Manager")

    # Load data
    df = get_all_specimens()

    if df.empty:
        st.info("No specimens found. Add some via the Telegram bot.")
        return

    # Create copy for display with clickable links
    display_df = df.copy()

    # Convert file paths to clickable links
    if 'photo_path' in display_df.columns:
        display_df['photo_path'] = display_df['photo_path'].apply(
            lambda x: f'<a href="file://{os.path.abspath(x)}" target="_blank">📷 View</a>'
            if x and os.path.exists(x) else '❌ Missing' if x else ''
        )

    if 'pdf_path' in display_df.columns:
        display_df['pdf_path'] = display_df['pdf_path'].apply(
            lambda x: f'<a href="{os.path.abspath(x)}" target="_blank">📄 View</a>'
            if x and os.path.exists(x) else '❌ Missing' if x else ''
        )

    # Display editable table
    st.header("Edit Specimens")
    location_list = ["илз", "уми", "102", "103", "3 эт", "подвал"]
    statuses_list = ["не начато", "передается в ИЛЗ", "изготовление", "изготовлено", "испытано"]
    statuses_list_4filter = ["🟠 не начато",  "🟡 передается в ИЛЗ", "🔵 изготовление", "🟢 изготовлено", "✅ испытано"]
    status_mapping = {
        "не начато": "🟠 не начато",
        "передается в ИЛЗ": "🟡 передается в ИЛЗ",
        "изготовление": "🔵 изготовление",
        "изготовлено": "🟢 изготовлено",
        "испытано": "✅ испытано"
    }
    dogovor_list = df['dogovor'].unique().tolist()
    # Configure columns for editing
    column_config = {
        "id": st.column_config.NumberColumn("ID", disabled=True,width=10),
        "status": st.column_config.SelectboxColumn(
            "Status",
            # options=statuses_list,
            options=list(status_mapping.values()),
            required=False,
            width=100
        ),
        "location": st.column_config.SelectboxColumn(
            "location",
            options=location_list,
            required=False,
            width=100
        ),
        "test_name": st.column_config.TextColumn("Test Name",width=50),
        "amount": st.column_config.NumberColumn("amount",width=10),
        "status_update_time": st.column_config.DatetimeColumn("Last Updated", disabled=True),
        "photo_path": st.column_config.LinkColumn("Photo", display_text="📷 View Photo",width=10),
        "pdf_path": st.column_config.LinkColumn("PDF", display_text="📄 View PDF",width=10),

    }
    with st.sidebar:
        #Status filter
        selected_statuses = st.multiselect(
            "Select statuses to display:",
            options=statuses_list_4filter,
            default=[],  # Empty by default to show all
        )

        # Contract filter
        selected_dogovors = st.multiselect(
            "Select contracts to display:",
            options=dogovor_list,
            default=[],  # Empty by default to show all
        )

        st.header("Attach Files to Specimen")

        col1, col2 = st.columns(2)

        with col1:
            specimen_id = st.selectbox("Select Specimen ID", df['id'].tolist(), key="file_upload")

            # Get specimen info for naming
            specimen_info = get_specimen_info(specimen_id)
            if specimen_info:
                test_name, dogovor = specimen_info
                st.info(f"Specimen: {test_name} - {dogovor}")

        with col2:
            uploaded_file = st.file_uploader(
                "Choose any file",
                type=None,  # Allow all file types
                key="file_uploader",
                accept_multiple_files=False  # Single file for simplicity
            )

        if uploaded_file is not None and specimen_id:
            if st.button("📎 Upload File"):
                if handle_file_upload(specimen_id, uploaded_file, test_name, dogovor):
                    st.success(f"✅ File '{uploaded_file.name}' uploaded successfully for ID {specimen_id}")
                else:
                    st.error("❌ Failed to upload file")

        # Display attached files
        st.subheader("📁 Attached Files")
        files = get_specimen_files(specimen_id)

        if files:
            for file_id, file_type, file_path, original_filename, upload_time in files:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{original_filename}** ({file_type}) - {upload_time}")
                with col2:
                    if os.path.exists(file_path):
                        st.download_button(
                            "📥 Download",
                            data=open(file_path, "rb"),
                            file_name=original_filename,
                            key=f"dl_{file_id}"
                        )
                with col3:
                    if st.button("🗑️", key=f"del_{file_id}"):
                        # Add delete functionality here
                        pass
        else:
            st.info("No files attached to this specimen")


    if selected_statuses:
        filtered_df = df[df['status'].isin(selected_statuses)]
    else:
        filtered_df = df

        # Apply contract filter on top of status filter
    if selected_dogovors:
        filtered_df = filtered_df[filtered_df['dogovor'].isin(selected_dogovors)]


    # Use st.markdown with unsafe_allow_html to render the clickable links
    # st.markdown(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)
    # For editing, use the original dataframe without HTML links
    st.subheader("Edit Data")
    column_order = ["id","test_name",'amount',"notes",'dogovor','location', "status", "status_update_time", "photo_path", "pdf_path"]

    edited_df = st.data_editor(
        filtered_df,  # Use original dataframe for editing
        column_config=column_config,
        column_order=column_order,
        hide_index=True,
        use_container_width=True,
        key="data_editor_key",
        num_rows="dynamic"
    )
    all_columns = [col for col in edited_df.columns if col != 'id']

    # Build the dynamic INSERT statement
    placeholders = ', '.join(['?'] * len(all_columns))
    column_names = ', '.join(all_columns)
    # Debug information
    if 'data_editor' in st.session_state:
        st.write("Edited data in session state:", st.session_state['data_editor'])
        st.write("Original data type:", type(df))
        st.write("Edited data type:", type(st.session_state['data_editor']))
    # Save button for table edits
    if st.button("💾 Save All Table Changes"):
        save_edited_specimens_simple(edited_df, df)
        # st.rerun()
    st.header("📷 Specimen Photos")
    
    for index, row in df.iterrows():
        display_specimen_with_local_files(row, UPLOAD_DIR)



if __name__ == '__main__':
    main()