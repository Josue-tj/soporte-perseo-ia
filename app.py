import os
import time
import json
import sqlite3
from PIL import Image
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ==========================================
# 1. GESTIÓN DE BASE DE DATOS (SQLITE)
# ==========================================
DB_NAME = "perseo_chat.db"

def init_db():
    """Inicializa la base de datos y crea la tabla si no existe."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            content TEXT
        )
    ''')
    conn.commit()
    conn.close()

def guardar_y_limpiar_mensaje(role, content, max_mensajes=50):
    """Guarda un mensaje y aplica la regla de borrar el más antiguo si supera el límite (FIFO)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO historial (role, content) VALUES (?, ?)", (role, content))
    cursor.execute("SELECT COUNT(*) FROM historial")
    total_mensajes = cursor.fetchone()[0]
    
    if total_mensajes > max_mensajes:
        excess = total_mensajes - max_mensajes
        cursor.execute("""
            DELETE FROM historial 
            WHERE id IN (SELECT id FROM historial ORDER BY id ASC LIMIT ?)
        """, (excess,))
        
    conn.commit()
    conn.close()

def cargar_historial_db():
    """Carga todo el historial guardado en la base de datos para mostrarlo en Streamlit."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM historial ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    
    return [{"role": row[0], "content": row[1]} for row in rows]

def vaciar_db():
    """Elimina todos los mensajes guardados en la base de datos."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM historial")
    conn.commit()
    conn.close()

init_db()


# ==========================================
# 2. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Perseo AI Master - GPT-4o",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==========================================
# 3. CARGA LOCAL DEL REPOMIX EN MEMORIA
# ==========================================
@st.cache_data
def cargar_repomix_local():
    """Lee el archivo repomix-output.txt localmente para inyectarlo directo en el contexto de GPT-4o."""
    if os.path.exists("repomix-output.txt"):
        with open("repomix-output.txt", "r", encoding="utf-8") as f:
            return f.read()
    return "No se encontró el archivo repomix-output.txt en el directorio."

repomix_data = cargar_repomix_local()

SYSTEM_PROMPT = f"""
Eres 'Perseo AI Assistant Master', arquitecto de software senior, DBA experto y desarrollador principal del ecosistema completo de Perseo ERP (Perseo PC, Perseo Web y Perseo Móvil).

CONTEXTO TÉCNICO PERMANENTE (CÓDIGO FUENTE Y BASE DE DATOS):
Tienes integrado y memorizado el siguiente volcado completo del sistema (repomix-output.txt). Analiza y ten en cuenta cada tabla, columna, relación, módulo, clase y servicio aquí contenidos:
--------------------------------------------------
{repomix_data}
--------------------------------------------------

REGLAS ABSOLUTAS DE OPERACIÓN (¡CRÍTICO - CERO ALUCINACIONES!):
1. PROHIBIDO INVENTAR NOMBRES DE TABLAS: Tienes prohibido usar nombres estándar o genéricos (como 'articulos', 'clientes', 'facturas') por intuición. Estás obligado a buscar en el volcado anterior el nombre exacto, real y case-sensitive de la tabla y sus columnas.
2. MOTOR DE BASE DE DATOS EXCLUSIVO: Trabajas ÚNICAMENTE con MySQL / MariaDB.
   - NUNCA uses corchetes [] para los nombres de columnas.
   - NUNCA uses la cláusula TOP. Usa LIMIT al final.
   - NUNCA uses ISNULL(). Usa IFNULL() o COALESCE().
3. PRECISIÓN TOTAL: Debes responder con exactitud quirúrgica sobre cuántos ítems, servicios o componentes conforman el sistema analizado basándote estrictamente en el código proporcionado.
4. IDIOMA: Responde siempre en español técnico y directo.

ESTRUCTURA DE RESPUESTA ESPERADA:
📍 **Módulo / Tabla Real:** [Nombre exacto extraído del código fuente o base de datos]
🛠️ **Diagnóstico Técnico:** [Explicación detallada]
💻 **Código / Consulta SQL:** [Sintaxis 100% verificada contra el volcado real]
💡 **Nota de Arquitectura:** [Validación breve]
"""


# ==========================================
# 4. ESTILOS CSS
# ==========================================
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    .stApp {
        background-color: #131314;
        color: #e3e3e3;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    header[data-testid="stHeader"] {
        background: transparent !important;
        z-index: 99999 !important;
    }

    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapseButton"] {
        visibility: visible !important;
        display: flex !important;
        color: #ffffff !important;
        background-color: #1e1f20 !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 10px !important;
        margin: 10px !important;
    }

    section[data-testid="stSidebar"] {
        background-color: #1e1f20;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    .header-title {
        background: linear-gradient(135deg, #10b981 0%, #3b82f6 50%, #6366f1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        font-weight: 700;
        letter-spacing: -0.8px;
        margin-bottom: 0px;
    }

    .subtext {
        color: #8e918f;
        font-size: 1.1rem;
        margin-top: 4px;
        margin-bottom: 25px;
    }

    .stChatMessage {
        background-color: transparent !important;
        border: none !important;
        padding: 1rem 0rem !important;
    }

    .openai-badge {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ==========================================
# 5. CONFIGURACIÓN API OPENAI
# ==========================================
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    try:
        openai_api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass

if "messages" not in st.session_state:
    st.session_state.messages = cargar_historial_db()

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None


# ==========================================
# 6. SIDEBAR Y UI
# ==========================================
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; padding: 10px 0;">
        <div style="font-size: 24px;">🧠</div>
        <div>
            <h3 style="margin:0; font-size: 1.1rem; color: #e3e3e3;">Perseo Master GPT-4o</h3>
            <span style="font-size: 0.75rem; color: #8e918f;">Memoria Total del Codebase</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()

    if openai_api_key:
        st.markdown('<div class="openai-badge">🟢 OpenAI GPT-4o Conectado</div>', unsafe_allow_html=True)
    else:
        st.error("🔴 Falta OPENAI_API_KEY en .env o secrets")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📷 Adjuntar Captura de Pantalla")
    attached_image = st.file_uploader(
        "Sube una imagen del error:",
        type=["jpg", "png", "jpeg"],
        help="GPT-4o analizará la imagen junto con todo el contexto del sistema."
    )

    image_preview = None
    if attached_image:
        image_preview = Image.open(attached_image)
        st.image(image_preview, caption="Imagen Adjunta", use_container_width=True)

    st.divider()
    st.markdown("### 🌐 Servicios SRI Ecuador")
    st.caption("• WebService Recepción: **En línea**")
    st.caption("• WebService Autorización: **En línea**")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Limpiar Conversación", use_container_width=True):
        vaciar_db()
        st.session_state.messages = []
        st.session_state.pending_prompt = None
        st.rerun()

st.markdown("""
<div style="padding-top: 10px;">
    <h1 class="header-title">Perseo AI Codebase Master</h1>
    <p class="subtext">Conectado directamente al código fuente y base de datos con GPT-4o.</p>
</div>
""", unsafe_allow_html=True)


# ==========================================
# 7. CHIPS DE SUGERENCIA Y MENSAJES
# ==========================================
if len(st.session_state.messages) == 0:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🔑 Error Firma Caducada\n\n'La firma electrónica se encuentra revocada'", key="chip1", use_container_width=True):
            st.session_state.pending_prompt = "El cliente reporta: Error al firmar la factura, indica 'La firma electrónica se encuentra caducada o expirada'."
            st.rerun()

    with col2:
        if st.button("🌐 WebService SRI 500\n\n'Error 500 de comunicación SRI'", key="chip2", use_container_width=True):
            st.session_state.pending_prompt = "Tengo un problema al enviar retención: 'Error 500 de comunicación con la base de datos o WebService del SRI'."
            st.rerun()

    with col3:
        if st.button("📊 Consulta de Artículos\n\n'Nombre correcto de tabla de productos'", key="chip3", use_container_width=True):
            st.session_state.pending_prompt = "Dime exactamente cuál es el nombre de la tabla de productos y dame la consulta SQL para consultar el stock y precio."
            st.rerun()

    with col4:
        if st.button("🔢 Secuencia Duplicada\n\n'Número de comprobante duplicado'", key="chip4", use_container_width=True):
            st.session_state.pending_prompt = "El sistema muestra: 'Error de clave de acceso o secuencia de comprobante duplicada'."
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

for msg in st.session_state.messages:
    avatar = "🧠" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        if "image" in msg and msg["image"] is not None:
            st.image(msg["image"], width=300)
        st.markdown(msg["content"])


# ==========================================
# 8. LLAMADA A OPENAI GPT-4O
# ==========================================
user_prompt = st.chat_input("Escribe tu consulta o error sobre Perseo...")

if st.session_state.pending_prompt and not user_prompt:
    user_prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if user_prompt:
    guardar_y_limpiar_mensaje("user", user_prompt)
    
    user_msg_data = {"role": "user", "content": user_prompt}
    if image_preview is not None:
        user_msg_data["image"] = image_preview

    st.session_state.messages.append(user_msg_data)

    with st.chat_message("user", avatar="👤"):
        if image_preview is not None:
            st.image(image_preview, width=300)
        st.markdown(user_prompt)

    with st.chat_message("assistant", avatar="🧠"):
        message_placeholder = st.empty()
        message_placeholder.markdown("*(Analizando codebase y esquema con GPT-4o...)*")

        try:
            if not openai_api_key:
                raise ValueError("Configura tu OPENAI_API_KEY en el entorno o en st.secrets.")

            client = OpenAI(api_key=openai_api_key)

            # Construir mensajes para OpenAI
            messages_payload = [{"role": "system", "content": SYSTEM_PROMPT}]
            
            for past_msg in st.session_state.messages:
                role = "user" if past_msg["role"] == "user" else "assistant"
                messages_payload.append({"role": role, "content": past_msg["content"]})

            response = client.chat.completions.create(
                model="gpt-4o",  # Modelo de altísima potencia con contexto masivo
                messages=messages_payload,
                temperature=0.1
            )

            answer = response.choices.message.content
            message_placeholder.markdown(answer)
            
            guardar_y_limpiar_mensaje("assistant", answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

        except Exception as e:
            error_msg = f"**Error al conectar con OpenAI:** {str(e)}"
            message_placeholder.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
