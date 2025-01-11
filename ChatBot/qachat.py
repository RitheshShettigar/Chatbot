# Q&A Chatbot with Image Upload and MySQL Integration (XAMPP)
from dotenv import load_dotenv
import streamlit as st
import os
from datetime import datetime
from PIL import Image
import mysql.connector
import google.generativeai as genai
import pandas as pd

# Load environment variables
load_dotenv()

# Configure Google Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    st.error("Google API Key not found. Ensure it's defined in the .env file.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# MySQL Database Connection
def init_db():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="chat"
    )
    cursor = conn.cursor()
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS interactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_question TEXT,
            bot_response TEXT,
            image_path VARCHAR(255),
            is_deleted TINYINT(1) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS personal_details (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(255),
            email VARCHAR(255),
            phone VARCHAR(50),
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_feedback TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    
    ''')
    cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS daily_activity (
        id INT AUTO_INCREMENT PRIMARY KEY,
        activity_date DATE,
        activity_type VARCHAR(255),
        count INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()  # Initialize database connection

# Helper Functions
def save_to_db(cursor, conn, user_question, bot_response, image_path):
    try:
        cursor.execute(''' 
            INSERT INTO interactions (user_question, bot_response, image_path)
            VALUES (%s, %s, %s)
        ''', (user_question, bot_response, image_path))
        conn.commit()
    except Exception as e:
        st.error(f"Failed to save to database: {e}")
#chat End


def get_daily_activity_data(cursor):
    # Updated query to fetch all data
    cursor.execute("SELECT activity_date, activity_type, count FROM daily_activity ORDER BY activity_date")
    rows = cursor.fetchall()
    
    # Debugging: Check if the rows are as expected
    print("Rows:", rows)
    
    if not rows:
        print("No data returned.")
        return pd.DataFrame(columns=["Date", "Activity Type", "Count"])
    
    # Create DataFrame with the returned data
    data = pd.DataFrame(rows, columns=["Date", "Activity Type", "Count"])
    return data







#personal Deatils
def save_personal_details_to_db(cursor, conn, full_name, email, phone, address):
    try:
        cursor.execute(''' 
            INSERT INTO personal_details (full_name, email, phone, address)
            VALUES (%s, %s, %s, %s)
        ''', (full_name, email, phone, address))
        conn.commit()
    except Exception as e:
        st.error(f"Failed to save personal details: {e}")
#personal Deatils End


#Feedback
def save_feedback_to_db(cursor, conn, feedback):
    try:
        cursor.execute(''' 
            INSERT INTO feedback (user_feedback)
            VALUES (%s)
        ''', (feedback,))
        conn.commit()
    except Exception as e:
        st.error(f"Failed to save feedback: {e}")

#Feedback End

def get_gemini_response(question):
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(question)
        return response.text
    except Exception as e:
        st.error(f"Error communicating with Gemini API: {e}")
        return None

def move_to_recycle_bin_single(cursor, conn, interaction_id):
    try:
        cursor.execute("UPDATE interactions SET is_deleted = 1 WHERE id = %s", (interaction_id,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Failed to move chat to recycle bin: {e}")
        return False

def move_to_recycle_bin(cursor, conn):
    try:
        cursor.execute("UPDATE interactions SET is_deleted = 1 WHERE is_deleted = 0")
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Failed to move chat history to recycle bin: {e}")
        return False

def restore_from_recycle_bin_single(cursor, conn, interaction_id):
    try:
        cursor.execute("UPDATE interactions SET is_deleted = 0 WHERE id = %s", (interaction_id,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Failed to restore chat: {e}")
        return False

def delete_permanently(cursor, conn):
    try:
        cursor.execute("DELETE FROM interactions WHERE is_deleted = 1")
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Failed to permanently delete chat history: {e}")
        return False

def show_recycle_bin(cursor):
    cursor.execute("SELECT * FROM interactions WHERE is_deleted = 1 ORDER BY created_at DESC")
    rows = cursor.fetchall()
    st.subheader("Recycle Bin:")
    if rows:
        for row in rows:
            st.write(f"**Question:** {row[1]}")
            st.write(f"**Response:** {row[2]}")
            if row[3]:
                st.image(row[3], caption="Uploaded Image", use_column_width=True)
            st.write(f"**Timestamp:** {row[5]}")
            
            # Individual buttons for Restore and Permanently Delete for each chat
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Restore (ID: {row[0]})", key=f"restore_{row[0]}", use_container_width=True):
                    if restore_from_recycle_bin_single(cursor, conn, row[0]):
                        st.success(f"Chat with ID {row[0]} restored successfully!")
            with col2:
                if st.button(f"Delete Permanently (ID: {row[0]})", key=f"delete_{row[0]}", use_container_width=True):
                    if delete_permanently(cursor, conn):
                        st.success(f"Chat with ID {row[0]} permanently deleted!")
            st.write("---")
    else:
        st.info("Recycle bin is empty.")

def delete_chat_history(cursor, conn):
    try:
        cursor.execute("DELETE FROM interactions")
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Failed to delete chat history: {e}")
        return False

def show_chat_history(cursor):
    cursor.execute("SELECT * FROM interactions WHERE is_deleted = 0 ORDER BY created_at DESC")
    rows = cursor.fetchall()
    st.subheader("Chat History:")
    if rows:
        for row in rows:
            st.write(f"**Question:** {row[1]}")
            st.write(f"**Response:** {row[2]}")
            if row[3]:
                st.image(row[3], caption="Uploaded Image", use_column_width=True)
            st.write(f"**Timestamp:** {row[5]}")
            
            # Button to move chat to Recycle Bin
            if st.button(f"Move to Recycle Bin (ID: {row[0]})", key=f"move_{row[0]}", use_container_width=True):
                if move_to_recycle_bin_single(cursor, conn, row[0]):
                    st.success(f"Chat with ID {row[0]} moved to recycle bin!")
            st.write("---")
    else:
        st.info("No chat history found.")

# Streamlit App Setup
st.set_page_config(
    page_title="Chatbot",
    page_icon="logo.png",
    layout="wide"
)

# Custom button style with reduced width and new color using markdown
st.markdown("""
    <style>
    .stButton>button {
        background-color: #4CAF50;  /* Green color */
        color: white;
        border-radius: 8px;
        padding: 10px 20px;  /* Smaller padding */
        width: auto;  /* Auto width */
    }
    .stButton>button:hover {
        background-color: #45a049; /* Darker green for hover effect */
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar Navigation
with st.sidebar:
    st.title("Confident Dental")
    page = st.radio("Go to:", ["Home", "Chatbot", "Chat History", "Recycle Bin", "Feedback", "Settings"])

# Main Page Logic
# Function to get daily activity data for graphing

# Display daily activity graph on the home page
if page == "Home":
    st.header("Welcome to Confident Dental Chatbot")
    
    # Display the daily activity graph
    activity_data = get_daily_activity_data(cursor)

    if not activity_data.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        activity_data.groupby(['Date', 'Activity Type']).sum().unstack().plot(kind='bar', stacked=True, ax=ax)
        ax.set_title('Daily Activity')
        ax.set_xlabel('Date')
        ax.set_ylabel('Activity Count')
        ax.legend(title="Activity Type")
        
        # Convert plot to image for Streamlit
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        st.image(buf, use_column_width=True)
    else:
        st.write("No activity data available for the past 30 days.")

    st.write("Navigate using the sidebar to explore different functionalities of the chatbot application.")

elif page == "Chatbot":
    st.header("CONFIDENT DENTAL CHATBOT")

    # User Input Section
    question_input = st.text_input("INPUT:", key="question_input")

    # Image Upload Section
    uploaded_image = st.file_uploader("Upload an image (optional):", type=["jpg", "jpeg", "png"])

    # Submit Button
    if st.button("Ask the Question"):
        if question_input:
            st.write(f"**Your Question:** {question_input}")

            image_path = None
            if uploaded_image:
                image_dir = "uploaded_images"
                os.makedirs(image_dir, exist_ok=True)
                image_path = os.path.join(image_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_image.name}")
                with open(image_path, "wb") as f:
                    f.write(uploaded_image.read())
                st.image(image_path, caption="Uploaded Image", use_column_width=True)

            response = get_gemini_response(question_input)
            if response:
                st.subheader("The Response:")
                st.write(response)
                save_to_db(cursor, conn, question_input, response, image_path)
                st.success("Interaction saved to the database!")
        else:
            st.error("Please enter a question!")

elif page == "Chat History":
    show_chat_history(cursor)
    if st.button("Delete All Chat History"):
        if delete_chat_history(cursor, conn):
            st.success("Chat history deleted successfully!")

elif page == "Recycle Bin":
    show_recycle_bin(cursor)

elif page == "Feedback":
    st.header("Feedback")
    st.write("We value your feedback! Please let us know how we can improve.")
    feedback_input = st.text_area("Your Feedback:")
    if st.button("Submit Feedback"):
        if feedback_input:
            st.success("Thank you for your feedback!")
        else:
            st.error("Please enter your feedback before submitting.")

elif page == "Settings":
    st.header("Settings")
    
    # Personal Details Section
    st.subheader("Personal Details")
    
    # Collecting User Information
    name = st.text_input("Full Name")
    email = st.text_input("Email Address")
    phone = st.text_input("Phone Number")
    address = st.text_area("Address")
    
    # Submit Button for Saving Personal Details
    if st.button("Save Personal Details"):
        if name and email and phone and address:
            save_personal_details_to_db(cursor, conn, name, email, phone, address)
            st.success("Personal details saved successfully!")
        else:
            st.error("Please fill in all the fields.")
