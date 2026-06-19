import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import textwrap 
import psycopg2

def check_password():
    """Returns True if the user entered the correct password."""
    def password_entered():
        # Check if password matches the secret environment variable
        if st.session_state["password"] == st.secrets["admin_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Delete from memory for security
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: #636EFA;'>🔒 Restricted Access</h2>", unsafe_allow_html=True)
        st.text_input("Enter the institutional password:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("<h2 style='text-align: center; color: #636EFA;'>🔒 Restricted Access</h2>", unsafe_allow_html=True)
        st.text_input("Enter the institutional password:", type="password", on_change=password_entered, key="password")
        st.error("❌ Incorrect password. Access denied.")
        return False
    return True

# Stop execution if password is incorrect
if not check_password():
    st.stop()


st.title("Classroom Emotional Control Dashboard")

DB_URL = st.secrets["DB_URL"]
# Initial Configuration
DB_NAME = "classroom.db"

st.set_page_config(
    page_title="Monitor",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Associated Colors
COLORS = {
    'happy': '#00CC96',     
    'surprise': '#19D3F3',  
    'neutral': '#636EFA',   
    'sad': '#FFA15A',       
    'angry': '#EF553B',     
    'fear': '#AB63FA',      
    'disgust': '#FF6692'    
}

# CSS (Modified for White Background / Light Theme)
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; }
    
    .metric-card {
        background-color: #F8F9FA;
        border-radius: 10px;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        height: 140px;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        border: 1px solid #E0E0E0;
        margin-bottom: 1rem;
    }
    .metric-card h3 { color: #6C757D; font-size: 14px; margin: 0; text-transform: uppercase; letter-spacing: 1px;}
    .metric-card h2 { color: #212529; font-size: 38px; font-weight: 800; margin: 5px 0; }
    
    .advice-box {
        background-color: #F8F9FA;
        border-left: 5px solid;
        padding: 20px;
        border-radius: 8px;
        margin-top: 15px;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
    }
    .advice-title { font-weight: bold; font-size: 18px; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

if 'start_time' not in st.session_state: 
    st.session_state.start_time = datetime.now()


# Database Functions

def get_data_since_start():
    try:
        conn = psycopg2.connect(DB_URL)
        # Limit to 500 records to prevent web saturation
        df = pd.read_sql_query("SELECT timestamp, emotion, valence, arousal, dominance FROM emotions ORDER BY id DESC LIMIT 500", conn)
        conn.close()
        
        if df.empty: return pd.DataFrame()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        return pd.DataFrame()

def clear_database():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM emotions")
        conn.commit()
        conn.close()
        st.session_state.start_time = datetime.now()
        st.toast("Database successfully reset.", icon="✅")
    except Exception as e:
        st.error(f"Error clearing DB: {e}")

@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# Metrics Calculation
def calculate_metrics(df):
    if df.empty: 
        return 0, "...", ("WAITING FOR DATA...", "#666666"), pd.DataFrame(), "neutral", "...", "...", "...", "...", "...", "..."
    
    # Score conversion 
    def get_score(emo):
        if emo in ['neutral']: return 90     # Looking at board, reading, writing
        if emo in ['surprise']: return 85    # High interest
        if emo in ['happy']: return 70       # Positive but prone to distraction (laughter)
        if emo in ['sad']: return 35         # Boredom/Fatigue
        if emo in ['fear']: return 25        # Confusion/Anxiety
        if emo in ['angry', 'disgust']: return 20 # Frustration/Rejection
        return 50
        
    df['score'] = df['emotion'].apply(get_score)
    
    # 15-second windows
    tiempo_actual = df['timestamp'].max()
    df_reciente = df[df['timestamp'] >= tiempo_actual - timedelta(seconds=15)]
    df_anterior = df[(df['timestamp'] >= tiempo_actual - timedelta(seconds=30)) & (df['timestamp'] < tiempo_actual - timedelta(seconds=15))]
    
    if df_reciente.empty:
        df_reciente = df.tail(1)
        
    current_avg = int(df_reciente['score'].mean())
    avg_anterior = df_anterior['score'].mean() if not df_anterior.empty else current_avg
    
    # 1. Trend
    if current_avg > avg_anterior + 5: tendencia, tend_col = "RISING ⬆", "#00CC96"
    elif current_avg < avg_anterior - 5: tendencia, tend_col = "FALLING ⬇", "#EF553B"
    else: tendencia, tend_col = "STABLE ➖", "#6C757D"

    # 2. Dominant Emotion
    try:
        dom_en = df_reciente['emotion'].mode()[0]
        trans = {'happy':'HAPPY', 'neutral':'NEUTRAL', 'sad':'SAD', 
                 'angry':'FRUSTRATED', 'surprise':'SURPRISED', 'fear':'FEAR', 'disgust':'DISGUST'}
        dom_es = trans.get(dom_en, dom_en.upper())
    except: dom_es, dom_en = "...", "neutral"

    # 3. Arousal and Valence
    aro_avg = df_reciente['arousal'].mean() if 'arousal' in df_reciente.columns else 0
    val_avg = df_reciente['valence'].mean() if 'valence' in df_reciente.columns else 0
    
    energia = "HIGH (Active)" if aro_avg > 0.2 else "LOW (Sleepy)" if aro_avg < -0.2 else "MEDIUM"
    disposicion = "POSITIVE" if val_avg > 0.1 else "NEGATIVE" if val_avg < -0.1 else "NEUTRAL"

    # 4. Traffic Light Status
    if current_avg >= 75: 
        status, status_col = "OPTIMAL STATE", "#00CC96"
        razon = f"The average attention is {current_avg}%. The majority of the class is in a '{dom_es}' state."
        sugerencia = "Ideal moment to introduce new, theoretical, or complex concepts, as receptivity is at its peak."
    elif current_avg >= 50: 
        status, status_col = "MEDIUM ATTENTION", "#FFA15A"
        razon = f"Attention level dropped to {current_avg}%. An increase in distraction or '{dom_es}' is detected."
        sugerencia = "Ask the class a participatory question or use a real-life practical example to regain full focus."
    else: 
        status, status_col = "CRITICAL STATE", "#EF553B"
        razon = f"Alert! Attention at {current_avg}%. High levels of fatigue, distraction, or '{dom_es}' are detected."
        sugerencia = "Take a 2-minute active break, change the class dynamic (group work/debate), or ask if there are any questions."

    # 5. Charts
    if not df.empty:
        dist_counts = df['emotion'].value_counts().reset_index()
        dist_counts.columns = ['Emotion', 'Count']
        total = dist_counts['Count'].sum()
        dist_counts['Percentage'] = (dist_counts['Count'] / total * 100).round(1)
        dist_counts['Label'] = dist_counts['Emotion'].map(
            {'happy':'Happy', 'neutral':'Neutral', 'sad':'Sad', 
             'angry':'Frustrated', 'surprise':'Surprise', 'fear':'Fear', 'disgust':'Disgust'}
        ).fillna('Other')
        dist_counts = dist_counts.sort_values('Percentage', ascending=False)
        return current_avg, dom_es, (status, status_col), dist_counts, dom_en, tendencia, tend_col, energia, disposicion, razon, sugerencia
    
    return current_avg, dom_es, (status, status_col), pd.DataFrame(), dom_en, tendencia, tend_col, energia, disposicion, razon, sugerencia


# Sidebar Control Panel
with st.sidebar:
    st.header("System Control")
    
    modo_vista = st.radio(
        "View Mode:",
        ("Traffic Light View", "Modules View", "Session Analysis")
    )
    
    st.markdown("---")
    st.subheader("Data Administration")
    
    df_sidebar = get_data_since_start()
    if not df_sidebar.empty:
        csv_data = convert_df_to_csv(df_sidebar)
        st.download_button(
            label="Download Report (CSV)",
            data=csv_data,
            file_name=f"class_report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.button("Download Report (CSV)", disabled=True, use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("CLEAR DATABASE", type="primary", use_container_width=True):
        clear_database()
        st.rerun()

# Rendering

def renderizar_semaforo():
    df = get_data_since_start()
    att_score, _, (status_text, status_col), _, _, _, _, _, _, razon, sugerencia = calculate_metrics(df)
    
    c1, c2 = st.columns([1, 1.5])
    
    with c1:
        html_semaforo = f"""
        <div style="display: flex; justify-content: center; align-items: center; height: 100%; flex-direction: column;">
            <div style="background-color: {status_col}; width: 220px; height: 220px; border-radius: 50%; display: flex; justify-content: center; align-items: center; box-shadow: 0px 0px 40px {status_col}; margin-bottom: 20px;">
            </div>
            <h1 style="color: {status_col}; text-align: center; font-size: 3rem; font-weight: bold; margin:0;">{status_text}</h1>
            <h3 style="color: #6C757D; margin-top: 5px;">Attention Level: {att_score}%</h3>
        </div>
        """
        st.markdown(html_semaforo, unsafe_allow_html=True)
        
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Reason / Diagnosis
        st.markdown(f"""
        <div class="advice-box" style="border-color: #636EFA;">
            <div class="advice-title" style="color: #636EFA;">Classroom Diagnosis:</div>
            <div style="color: #212529; font-size: 16px;">{razon}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Suggestion
        st.markdown(f"""
        <div class="advice-box" style="border-color: {status_col};">
            <div class="advice-title" style="color: {status_col};">Pedagogical Suggestion:</div>
            <div style="color: #212529; font-size: 16px;">{sugerencia}</div>
        </div>
        """, unsafe_allow_html=True)


def renderizar_modulos():
    df = get_data_since_start()
    att_score, dom_text, (status_text, status_col), _, dom_key, tendencia, tend_col, energia, disposicion, _, _ = calculate_metrics(df)
    
    score_color = "#00CC96" if att_score > 60 else ("#FFA15A" if att_score > 40 else "#EF553B")
    dom_color = COLORS.get(dom_key, "#333333")
    
    # Row 1
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="metric-card" style="border-top: 4px solid {score_color}"><h3>Current Attention</h3><h2 style="color:{score_color}">{att_score}%</h2></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card" style="border-top: 4px solid {dom_color}"><h3>Dominant State</h3><h2 style="color:{dom_color};font-size:30px;">{dom_text}</h2></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card" style="border-top: 4px solid {status_col}"><h3>Condition</h3><h2 style="color:{status_col};font-size:26px;">{status_text}</h2></div>', unsafe_allow_html=True)
    
    # Row 2
    c4, c5, c6 = st.columns(3)
    c4.markdown(f'<div class="metric-card" style="border-top: 4px solid #19D3F3"><h3>Energy (Arousal)</h3><h2 style="color:#19D3F3;font-size:26px;">{energia}</h2></div>', unsafe_allow_html=True)
    c5.markdown(f'<div class="metric-card" style="border-top: 4px solid #AB63FA"><h3>Disposition (Valence)</h3><h2 style="color:#AB63FA;font-size:26px;">{disposicion}</h2></div>', unsafe_allow_html=True)
    c6.markdown(f'<div class="metric-card" style="border-top: 4px solid {tend_col}"><h3>Attention Trend</h3><h2 style="color:{tend_col};font-size:26px;">{tendencia}</h2></div>', unsafe_allow_html=True)

# Analysis View

def renderizar_analisis():
    df = get_data_since_start()
    if df.empty:
        st.warning("Waiting for data to start analysis...")
        return
        
    att_score, dom_text, (status_text, status_col), df_dist, dom_key, _, _, _, _, _, _ = calculate_metrics(df)
    
    col_L, col_R = st.columns([3, 2]) 
    
    with col_L:
        st.markdown("### VAD Dimensions (Temporal Evolution)")
        df['Minutes'] = (df['timestamp'] - st.session_state.start_time).dt.total_seconds() / 60.0
        
        df_temporal = df[['Minutes', 'valence', 'arousal', 'dominance']].set_index('Minutes')
        df_suavizado = df_temporal.rolling(window=10, min_periods=1).mean()
        df_suavizado.columns = ['Valence', 'Arousal', 'Dominance']
        
        tiempo_maximo = df_suavizado.index.max()
        if tiempo_maximo >= 1.0:
            df_grafica = df_suavizado[df_suavizado.index >= (tiempo_maximo - 1.0)]
        else:
            df_grafica = df_suavizado
        
        st.line_chart(df_grafica, color=["#00CC96", "#636EFA", "#AB63FA"])

    with col_R:
        st.markdown("### State History (Accumulated)")
        html_content = '<div style="background-color: #F8F9FA; border-radius: 10px; padding: 15px; height: 350px; overflow-y: auto; border: 1px solid #E0E0E0;">'
        
        for index, row in df_dist.iterrows():
            emo = row['Emotion']
            pct = row['Percentage']
            label = row['Label']
            color = COLORS.get(emo, '#555')
            
            bar_html = textwrap.dedent(f"""
                <div style="margin-bottom: 12px;">
                    <div style="display:flex; justify-content: space-between; color: #212529; font-family: sans-serif; font-size: 14px; font-weight: bold; margin-bottom: 4px;">
                        <span>{label}</span>
                        <span>{pct}%</span>
                    </div>
                    <div style="background-color: #E9ECEF; border-radius: 5px; width: 100%; height: 20px;">
                        <div style="background-color: {color}; width: {pct}%; height: 100%; border-radius: 5px;"></div>
                    </div>
                </div>
            """)
            html_content += bar_html
        
        html_content += "</div>"
        st.markdown(html_content, unsafe_allow_html=True)


# ==========================================
# ROUTES AND SLEEP MODE (REAL-TIME SUPERVISOR)
# ==========================================

# Runs every 2 seconds automatically
@st.fragment(run_every=2)
def supervisor_pantalla():
    df_check = get_data_since_start()
    
    # Calculate seconds since the last data arrived
    if not df_check.empty:
        tiempo_ultimo_registro = df_check['timestamp'].max()
        diferencia_segundos = (datetime.now() - tiempo_ultimo_registro).total_seconds()
    else:
        diferencia_segundos = 999 # Assumed off if no data

    # If > 15 seconds without data
    if diferencia_segundos > 15:
        st.markdown("""
            <div style="text-align: center; padding: 60px; background-color: #F8F9FA; border-radius: 15px; margin-top: 50px; border: 2px dashed #636EFA;">
                <h1 style="color: #636EFA; font-size: 3.5rem;">🌙 SYSTEM IN SLEEP MODE</h1>
                <h3 style="color: #6C757D; margin-bottom: 20px;">Local Artificial Intelligence processing is inactive.</h3>
                <p style="color: #212529; font-size: 1.2rem;">Waiting for real-time connection from the institution's camera...</p>
                <p style="color: #6C757D; font-size: 0.9rem;">(Privacy protection activated: No images are stored in the cloud)</p>
            </div>
        """, unsafe_allow_html=True)
    
    # If camera is ON and sending data (less than 15s diff)
    else:
        if modo_vista == "Traffic Light View":
            renderizar_semaforo()
        elif modo_vista == "Modules View":
            renderizar_modulos()
        elif modo_vista == "Session Analysis":
            renderizar_analisis()

# Execute supervisor
supervisor_pantalla()
