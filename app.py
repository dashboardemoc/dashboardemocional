import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import textwrap 
import psycopg2
from sqlalchemy import create_engine
import pytz
import plotly.express as px
import plotly.graph_objects as go
# ==========================================
# CONTROL DE ACCESO (LOGIN MEJORADO)
# ==========================================
def check_password():
    """Retorna True si el usuario ingresó la contraseña correcta."""
    
    # Si ya puso la clave antes, entra directo
    if st.session_state.get("password_correct", False):
        return True

    # Interfaz gráfica del Login
    st.markdown("<h2 style='text-align: center; color: #636EFA;'>Monitor Académico - Acceso Restringido</h2>", unsafe_allow_html=True)
    
    # Usamos st.form para evitar que se recargue por accidente al tocar el "ojito"
    with st.form("login_form"):
        pwd = st.text_input("Ingrese la clave  de la institucion:", type="password")
        # Creamos un botón gigante y elegante
        submit_button = st.form_submit_button("Ingresar al Sistema", type="primary")
        
        if submit_button:
            if pwd == st.secrets["admin_password"]:
                st.session_state["password_correct"] = True
                st.rerun()  # Recarga la página y te deja entrar
            else:
                st.error("Clave incorrecta. Acceso denegado.")
    
    return False

# AQUÍ SE PONE LA BARRERA
if not check_password():
    st.stop()




DB_URL = st.secrets["DB_URL"]
# Configuracion inicial
DB_NAME = "classroom.db"

st.set_page_config(
    page_title="Monitor",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Colores asociados
COLORS = {
    'happy': '#00CC96',     
    'surprise': '#19D3F3',  
    'neutral': '#636EFA',   
    'sad': '#FFA15A',       
    'angry': '#EF553B',     
    'fear': '#AB63FA',      
    'disgust': '#FF6692'    
}

# CSS 
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    
    .metric-card {
        background-color: #262730;
        border-radius: 10px;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.3);
        text-align: center;
        height: 140px;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        border: 1px solid #333;
        margin-bottom: 1rem;
    }
    .metric-card h3 { color: #A3A8B8; font-size: 14px; margin: 0; text-transform: uppercase; letter-spacing: 1px;}
    .metric-card h2 { color: #FAFAFA; font-size: 38px; font-weight: 800; margin: 5px 0; }
    
    .advice-box {
        background-color: #262730;
        border-left: 5px solid;
        padding: 20px;
        border-radius: 8px;
        margin-top: 15px;
    }
    .advice-title { font-weight: bold; font-size: 18px; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

if 'start_time' not in st.session_state: 
    zona_peru = pytz.timezone('America/Lima')
    st.session_state.start_time = datetime.now(zona_peru).replace(tzinfo=None)


# Base de datos

# Creamos el motor fuera de la función para que sea más rápido
engine = create_engine(st.secrets["DB_URL"])

def get_data_since_start():
    try:
        # Usamos el engine en lugar del conn de psycopg2
        df = pd.read_sql_query("SELECT timestamp, emotion, valence, arousal, dominance FROM emotions ORDER BY id DESC LIMIT 500", engine)
        if df.empty: return pd.DataFrame()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        return pd.DataFrame()

def clear_database():
    try:
        # 1. Nos conectamos a la Nube (Supabase)
        conn = psycopg2.connect(st.secrets["DB_URL"])
        cursor = conn.cursor()
        
        # 2. Borramos todos los registros de la tabla
        cursor.execute("DELETE FROM emotions")
        conn.commit()
        conn.close()
        
        # 3. Reiniciamos el reloj de la clase con la hora exacta de Perú
        zona_peru = pytz.timezone('America/Lima')
        st.session_state.start_time = datetime.now(zona_peru).replace(tzinfo=None)
        
        st.toast("Base de datos en la nube reiniciada con éxito.", icon="✅")
    except Exception as e:
        st.error(f"Error limpiando BD en la nube: {e}")

@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# Calculo de metricas
def calculate_metrics(df):
    if df.empty: 
        return 0, "...", ("ESPERANDO DATOS...", "#666666"), pd.DataFrame(), "neutral", "...", "...", "...", "...", "...", "..."
    
    # Cambio a neutral alto 
    def get_score(emo):
        if emo in ['neutral']: return 90     # Mirando pizarra, leyendo, escribiendo
        if emo in ['surprise']: return 85    # Interés alto
        if emo in ['happy']: return 70       # Positivos pero propensos a distraccion (risas)
        if emo in ['sad']: return 35         # Aburrimiento/Cansancio
        if emo in ['fear']: return 25        # Confusión/Ansiedad
        if emo in ['angry', 'disgust']: return 20 # Frustración/Rechazo
        return 50
        
    df['score'] = df['emotion'].apply(get_score)
    
    # los 15 segundos (puede cambiar para hacerlo mas rapido)
    tiempo_actual = df['timestamp'].max()
    df_reciente = df[df['timestamp'] >= tiempo_actual - timedelta(seconds=15)]
    df_anterior = df[(df['timestamp'] >= tiempo_actual - timedelta(seconds=30)) & (df['timestamp'] < tiempo_actual - timedelta(seconds=15))]
    
    if df_reciente.empty:
        df_reciente = df.tail(1)
        
    current_avg = int(df_reciente['score'].mean())
    avg_anterior = df_anterior['score'].mean() if not df_anterior.empty else current_avg
    
    # 1 La tendencia
    if current_avg > avg_anterior + 5: tendencia, tend_col = "SUBIENDO ⬆", "#00CC96"
    elif current_avg < avg_anterior - 5: tendencia, tend_col = "BAJANDO ⬇", "#EF553B"
    else: tendencia, tend_col = "ESTABLE ➖", "#A3A8B8"

    # 2 La emocion dominante
    try:
        dom_en = df_reciente['emotion'].mode()[0]
        trans = {'happy':'FELIZ', 'neutral':'NEUTRAL', 'sad':'TRISTE', 
                 'angry':'FRUSTRADO', 'surprise':'SORPRENDIDO', 'fear':'MIEDO', 'disgust':'RECHAZO'}
        dom_es = trans.get(dom_en, dom_en.upper())
    except: dom_es, dom_en = "...", "neutral"

    # 3 Excitacion y Valencia
    aro_avg = df_reciente['arousal'].mean() if 'arousal' in df_reciente.columns else 0
    val_avg = df_reciente['valence'].mean() if 'valence' in df_reciente.columns else 0
    
    energia = "ALTA (Activos)" if aro_avg > 0.2 else "BAJA (Somnolientos)" if aro_avg < -0.2 else "MEDIA"
    disposicion = "POSITIVA" if val_avg > 0.1 else "NEGATIVA" if val_avg < -0.1 else "NEUTRAL"

    # 4.Semaforo
    if current_avg >= 75: 
        status, status_col = "ESTADO ÓPTIMO", "#00CC96"
        razon = f"La atención promedio es {current_avg}%. La mayoría del aula se encuentra en estado '{dom_es}'."
        sugerencia = "Momento ideal para introducir conceptos nuevos, teóricos o complejos, ya que la receptividad es máxima."
    elif current_avg >= 50: 
        status, status_col = "ATENCIÓN MEDIA", "#FFA15A"
        razon = f"El nivel de atención bajó al {current_avg}%. Se detecta un incremento de dispersión o '{dom_es}'."
        sugerencia = "Haga una pregunta participativa a la clase o utilice un ejemplo práctico de la vida real para recuperar el foco total."
    else: 
        status, status_col = "ESTADO CRÍTICO", "#EF553B"
        razon = f"¡Alerta! Atención al {current_avg}%. Se detectan altos niveles de fatiga, distracción o '{dom_es}'."
        sugerencia = "Realice una pausa activa de 2 minutos, cambie la dinámica de la clase (trabajo en grupo/debate) o pregunte si hay dudas."

    # 5 graficos
    if not df.empty:
        dist_counts = df['emotion'].value_counts().reset_index()
        dist_counts.columns = ['Emotion', 'Count']
        total = dist_counts['Count'].sum()
        dist_counts['Percentage'] = (dist_counts['Count'] / total * 100).round(1)
        dist_counts['Label'] = dist_counts['Emotion'].map(
            {'happy':'Feliz', 'neutral':'Neutral', 'sad':'Triste', 
             'angry':'Frustrado', 'surprise':'Sorpresa', 'fear':'Miedo', 'disgust':'Rechazo'}
        ).fillna('Otro')
        dist_counts = dist_counts.sort_values('Percentage', ascending=False)
        return current_avg, dom_es, (status, status_col), dist_counts, dom_en, tendencia, tend_col, energia, disposicion, razon, sugerencia
    
    return current_avg, dom_es, (status, status_col), pd.DataFrame(), dom_en, tendencia, tend_col, energia, disposicion, razon, sugerencia


# Panel de control
with st.sidebar:
    st.header("Control del Sistema")
    
    modo_vista = st.radio(
        "Modo de Visualización:",
        ("Vista de Semáforo", "Vista de Módulos", "Análisis de Sesión")
    )
    
    st.markdown("---")
    st.subheader("Administración de Datos")
    
    df_sidebar = get_data_since_start()
    if not df_sidebar.empty:
        csv_data = convert_df_to_csv(df_sidebar)
        st.download_button(
            label="Descargar Reporte (CSV)",
            data=csv_data,
            file_name=f"reporte_clase_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.button("Descargar Reporte (CSV)", disabled=True, use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("BORRAR BASE DE DATOS", type="primary", use_container_width=True):
        clear_database()
        st.rerun()

st.title("Tablero de Control Emocional")

# Renderizamiento

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
            <h3 style="color: #A3A8B8; margin-top: 5px;">Nivel de Atención: {att_score}%</h3>
        </div>
        """
        st.markdown(html_semaforo, unsafe_allow_html=True)
        
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Razon
        st.markdown(f"""
        <div class="advice-box" style="border-color: #636EFA;">
            <div class="advice-title" style="color: #636EFA;">Diagnóstico del Aula:</div>
            <div style="color: #FAFAFA; font-size: 16px;">{razon}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # La Sugerencia
        st.markdown(f"""
        <div class="advice-box" style="border-color: {status_col};">
            <div class="advice-title" style="color: {status_col};">Sugerencia Pedagógica:</div>
            <div style="color: #FAFAFA; font-size: 16px;">{sugerencia}</div>
        </div>
        """, unsafe_allow_html=True)


def renderizar_modulos():
    df = get_data_since_start()
    att_score, dom_text, (status_text, status_col), _, dom_key, tendencia, tend_col, energia, disposicion, _, _ = calculate_metrics(df)
    
    score_color = "#00CC96" if att_score > 60 else ("#FFA15A" if att_score > 40 else "#EF553B")
    dom_color = COLORS.get(dom_key, "#FAFAFA")
    
    #Fila 1
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="metric-card" style="border-top: 4px solid {score_color}"><h3>Atención Actual</h3><h2 style="color:{score_color}">{att_score}%</h2></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card" style="border-top: 4px solid {dom_color}"><h3>Estado Dominante</h3><h2 style="color:{dom_color};font-size:30px;">{dom_text}</h2></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card" style="border-top: 4px solid {status_col}"><h3>Condición</h3><h2 style="color:{status_col};font-size:26px;">{status_text}</h2></div>', unsafe_allow_html=True)
    
    #Fila 2
    c4, c5, c6 = st.columns(3)
    c4.markdown(f'<div class="metric-card" style="border-top: 4px solid #19D3F3"><h3>Energía (Arousal)</h3><h2 style="color:#19D3F3;font-size:26px;">{energia}</h2></div>', unsafe_allow_html=True)
    c5.markdown(f'<div class="metric-card" style="border-top: 4px solid #AB63FA"><h3>Disposición (Valencia)</h3><h2 style="color:#AB63FA;font-size:26px;">{disposicion}</h2></div>', unsafe_allow_html=True)
    c6.markdown(f'<div class="metric-card" style="border-top: 4px solid {tend_col}"><h3>Tendencia de Atención</h3><h2 style="color:{tend_col};font-size:26px;">{tendencia}</h2></div>', unsafe_allow_html=True)

# Vista de analisis

def renderizar_analisis():
    df = get_data_since_start()
    if df.empty:
        st.warning("Esperando datos para iniciar el análisis...")
        return
        
    att_score, dom_text, (status_text, status_col), df_dist, dom_key, _, _, _, _, _, _ = calculate_metrics(df)
    
    col_L, col_R = st.columns([3, 2]) 
    
    with col_L:
        st.markdown("### Dimensiones VAD (Evolución Temporal)")
        
        # 1. Usamos el tiempo REAL del reloj
        df_temporal = df[['timestamp', 'valence', 'arousal', 'dominance']].copy()
        df_temporal.set_index('timestamp', inplace=True)
        
        # 2. Suavizado de la curva (Rolling)
        df_suavizado = df_temporal.rolling(window=10, min_periods=1).mean()
        df_suavizado.columns = ['Valencia (Agrado)', 'Activación (Energía)', 'Dominancia']
        
        # 3. Filtrar para mostrar siempre solo el último minuto
        if not df_suavizado.empty:
            tiempo_maximo = df_suavizado.index.max()
            limite_tiempo = tiempo_maximo - pd.Timedelta(seconds=60)
            # Usamos .copy() para poder modificarlo sin alertas de Pandas
            df_grafica = df_suavizado[df_suavizado.index >= limite_tiempo].copy() 
        else:
            df_grafica = df_suavizado.copy()
        
# =====================================================================
        # SOLUCIÓN CON PLOTLY: Mantiene las etiquetas horizontales y limpias
        # =====================================================================
        if not df_grafica.empty:
            import plotly.graph_objects as go
            
            fig = go.Figure()
            
            # Mapeo de columnas y sus colores exactos
            columnas = ['Valencia (Agrado)', 'Activación (Energía)', 'Dominancia']
            colores = ["#00CC96", "#636EFA", "#AB63FA"]
            
            for col, color in zip(columnas, colores):
                fig.add_trace(go.Scatter(
                    x=df_grafica.index,  # Usamos el datetime original sin strftime
                    y=df_grafica[col],
                    mode='lines',
                    name=col,
                    line=dict(color=color, width=3),
                    hovertemplate='%{y:.2f}'
                ))
            
            # Configuración del estilo oscuro y comportamiento del eje X
            fig.update_layout(
                margin=dict(l=20, r=20, t=10, b=20),
                paper_bgcolor='rgba(0,0,0,0)', # Transparente para usar el fondo de Streamlit
                plot_bgcolor='rgba(0,0,0,0)',
                height=320,
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.3,
                    xanchor="center",
                    x=0.5,
                    font=dict(color="#A3A8B8")
                ),
                xaxis=dict(
                    tickformat='%H:%M:%S', # Formato elegante directamente en el renderizado
                    tickangle=0,           # Fuerza a que se queden horizontales
                    nticks=6,              # Muestra máximo 6 etiquetas distribuidas para evitar colapsos
                    gridcolor='#262730',
                    tickfont=dict(color="#A3A8B8")
                ),
                yaxis=dict(
                    gridcolor='#262730',
                    tickfont=dict(color="#A3A8B8"),
                    range=[-0.7, 0.1]      # Ajusta según los rangos que sueles manejar
                ),
                template="plotly_dark"
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    with col_R:
        st.markdown("### Historial de Estados (Acumulado)")
        html_content = '<div style="background-color: #262730; border-radius: 10px; padding: 15px; height: 350px; overflow-y: auto;">'
        
        for index, row in df_dist.iterrows():
            emo = row['Emotion']
            pct = row['Percentage']
            label = row['Label']
            color = COLORS.get(emo, '#555')
            
            bar_html = textwrap.dedent(f"""
                <div style="margin-bottom: 12px;">
                    <div style="display:flex; justify-content: space-between; color: #eee; font-family: sans-serif; font-size: 14px; font-weight: bold; margin-bottom: 4px;">
                        <span>{label}</span>
                        <span>{pct}%</span>
                    </div>
                    <div style="background-color: #444; border-radius: 5px; width: 100%; height: 20px;">
                        <div style="background-color: {color}; width: {pct}%; height: 100%; border-radius: 5px;"></div>
                    </div>
                </div>
            """)
            html_content += bar_html
        
        html_content += "</div>"
        st.markdown(html_content, unsafe_allow_html=True)


# ==========================================
# RUTAS Y MODO REPOSO (SUPERVISOR EN TIEMPO REAL)
# ==========================================

# ==========================================
# RUTAS Y MODO REPOSO (SUPERVISOR EN TIEMPO REAL)
# ==========================================
@st.fragment(run_every=2)
def supervisor_pantalla():
    df_check = get_data_since_start()
    
    # 🔴 SOLUCIÓN CLOUD: Obtener la hora exacta de Perú
    zona_peru = pytz.timezone('America/Lima')
    hora_actual_peru = datetime.now(zona_peru).replace(tzinfo=None)

    # Calculamos hace cuántos segundos llegó el último dato
    if not df_check.empty:
        tiempo_ultimo_registro = df_check['timestamp'].max()
        diferencia_segundos = (hora_actual_peru - tiempo_ultimo_registro).total_seconds()
    else:
        diferencia_segundos = 999 

    # Si pasaron más de 15 segundos sin recibir datos (Timeout)
    if diferencia_segundos > 15:
        st.markdown("""
            <div style="text-align: center; padding: 60px; background-color: #262730; border-radius: 15px; margin-top: 50px; border: 2px dashed #636EFA;">
                <h1 style="color: #636EFA; font-size: 3.5rem;">SISTEMA EN MODO REPOSO</h1>
                <h3 style="color: #A3A8B8; margin-bottom: 20px;">El procesamiento local de Inteligencia Artificial está inactivo.</h3>
                <p style="color: #FAFAFA; font-size: 1.2rem;">Esperando conexión en tiempo real desde la cámara de la institución...</p>
                <p style="color: #555; font-size: 0.9rem;">(No se almacenan imágenes en la nube)</p>
            </div>
        """, unsafe_allow_html=True)
    
    else:
        if modo_vista == "Vista de Semáforo":
            renderizar_semaforo()
        elif modo_vista == "Vista de Módulos":
            renderizar_modulos()
        elif modo_vista == "Análisis de Sesión":
            renderizar_analisis()

supervisor_pantalla()


