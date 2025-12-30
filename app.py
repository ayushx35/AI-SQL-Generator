import streamlit as st
import os
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_openai import ChatOpenAI
import sqlalchemy

st.set_page_config(page_title="Chat with DB", page_icon="🗄️", layout="wide")
st.title("🤖 Chat with your SQL Database")

# --- INITIALIZE SESSION STATE ---
if "chat_ready" not in st.session_state:
    st.session_state.chat_ready = False
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR: CONFIGURATION ---
st.sidebar.header("1. Database Config")

db_type = st.sidebar.selectbox("Select Database Type", ["PostgreSQL", "MySQL", "SQLite"])

# Fallback to Env variables if fields are empty
env_pass = os.getenv("DB_PASSWORD", "")
env_key = os.getenv("OPENAI_API_KEY", "")

if db_type == "SQLite":
    db_path = st.sidebar.text_input("Database File Path", value="sample_store.db")
else:
    db_host = st.sidebar.text_input("Host", value="10.192.88.52")
    db_user = st.sidebar.text_input("Username", value="postgres")
    db_password = st.sidebar.text_input("Password", type="password", value=env_pass)
    db_name = st.sidebar.text_input("Database Name", value="JioStaging")
    db_port = st.sidebar.text_input("Port", value="5432")

st.sidebar.header("2. AI Config")
api_key = st.sidebar.text_input("OpenAI API Key", type="password", value=env_key)

# --- CONNECTION LOGIC ---
if st.sidebar.button("Connect"):
    try:
        if db_type == "PostgreSQL":
            uri = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        elif db_type == "MySQL":
            uri = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        else:
            uri = f"sqlite:///{db_path}"

        engine = sqlalchemy.create_engine(uri)
        # Test connection
        with engine.connect() as conn:
            pass
        
        # Save to session state
        st.session_state.db = SQLDatabase(engine=engine)
        st.session_state.api_key = api_key
        st.session_state.chat_ready = True
        st.session_state.messages = [{"role": "assistant", "content": f"Connected to {db_name}! How can I help with your data today?"}]
        st.sidebar.success("Connected!")
    except Exception as e:
        st.sidebar.error(f"Error: {e}")

# --- CHAT INTERFACE ---
if st.session_state.chat_ready:
    # 1. Initialize the Agent
    llm = ChatOpenAI(
        model="gpt-4o-mini", 
        temperature=0, 
        openai_api_key=st.session_state.api_key
    )
    
    agent_executor = create_sql_agent(
        llm=llm,
        db=st.session_state.db,
        agent_type="openai-tools",
        verbose=True
    )

    # 2. Display Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 3. User Input Box (This should now show up at the bottom)
    if prompt := st.chat_input("Ask a question about your tables..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate Response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Run the LangChain agent
                    response = agent_executor.invoke({"input": prompt})
                    full_response = response["output"]
                    st.markdown(full_response)
                    # Add assistant response to history
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                except Exception as e:
                    error_msg = f"I ran into an error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
else:
    st.info("Please enter your credentials in the sidebar and click 'Connect' to begin.")