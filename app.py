import os
import time
import json
import sqlite3
from PIL import Image
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai

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
    page_title="Perseo IA - Soporte Conversacional",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==========================================
# 3. PROMPT DE SISTEMA Y GESTIÓN DE ARCHIVOS MASIVOS (FILES API)
# ==========================================
SYSTEM_PROMPT = """
Eres 'Perseo AI Assistant Master', especialista senior, desarrollador y experto en base de datos del ecosistema completo de Perseo ERP (Ecuador):
1. Perseo PC (Sistema de escritorio Windows)
2. Perseo Web (Plataforma en la Nube)
3. Perseo App Móvil (Android/iOS)

REGLAS OBLIGATORIAS DE TECNOLOGÍA Y SINTAXIS (¡CRÍTICO!):
1. MOTOR DE BASE DE DATOS EXCLUSIVO: Trabajas ÚNICAMENTE con MySQL / MariaDB.
   - NUNCA uses sintaxis de SQL Server o PostgreSQL.
   - NUNCA uses corchetes [] para los nombres de columnas o alias. Usa comillas simples '' para textos o backticks `` si es necesario.
   - NUNCA uses la función ISNULL(). Usa IFNULL() o COALESCE().
   - Para limitar resultados usa la cláusula LIMIT al final de la consulta (ej. LIMIT 10), NUNCA uses TOP.
2. LENGUAJE Y CÓDIGO FUENTE:
   - Apóyate estrictamente en el código fuente y en la estructura de la base de datos (.sql) proporcionados en el archivo adjunto (repomix-output.txt).
   - Usa los nombres exactos de tablas y columnas que existen en la base de datos de Perseo. NO inventes campos ni supongas estructuras.
3. IDIOMA Y FORMATO:
   - Responde SIEMPRE y EXCLUSIVAMENTE en idioma español.

CAPACIDADES Y ENFOQUE:
- Resolución de Errores y Soporte Técnico: Diagnosticas fallas operativas, de base de datos, licencias y SRI.
- Análisis y Corrección de Código: Si el usuario reporta un error, analiza el código provisto, indica el archivo afectado y entrega la corrección exacta.

ESTRUCTURA DE RESPUESTA ESPERADA:
📍 **Plataforma / Módulo:** [Indicar entorno, tabla o archivo afectado]
🛠️ **Diagnóstico y Solución:** [Explicación clara y directa del error]
💻 **Código / Consulta SQL:** [Código corregido o script SQL en sintaxis MySQL/MariaDB]
💡 **Nota Técnica:** [Recomendaciones breves de buenas prácticas]
"""

@st.cache_data
def cargar_kb_json():
    try:
        with open("perseo_kb.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

@st.cache_resource
def obtener_archivo_remoto_gemini(api_key_str):
    """Sube el archivo masivo repomix-output.txt a la Files API de Gemini para evitar el límite de tokens inline."""
    if not api_key_str:
        return None
    genai.configure(api_key=api_key_str)
    try:
        # Verificar si ya fue subido previamente en la cuenta
        for f in genai.list_files():
            if f.display_name == "repomix_output":
                return f
        # Subir el archivo completo sin recortes
        if os.path.exists("repomix-output.txt"):
            return genai.upload_file("repomix-output.txt", display_name="repomix_output")
    except Exception:
        pass
    return None


# ==========================================
# 4. ESTILOS CSS
# ==========================================
GEMINI_CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Outfit:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Outfit', 'Google Sans', sans-serif;
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

    [data-testid="collapsedControl"]:hover,
    [data-testid="stSidebarCollapseButton"]:hover {
        background-color: #28292a !important;
        border-color: #4285f4 !important;
    }

    section[data-testid="stSidebar"] {
        background-color: #1e1f20;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    .gemini-header-title {
        background: linear-gradient(135deg, #4285f4 0%, #9b51e0 50%, #d946ef 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        font-weight: 700;
        letter-spacing: -0.8px;
        margin-bottom: 0px;
    }

    .gemini-subtext {
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

    div[data-testid="stChatMessage"]:nth-child(even) {
        background-color: transparent !important;
    }

    .gemini-sparkle-icon {
        width: 32px;
        height: 32px;
        background: linear-gradient(135deg, #4285f4, #a855f7);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        box-shadow: 0 0 12px rgba(66, 133, 244, 0.4);
    }

    .stChatInputContainer {
        border-radius: 28px !important;
        background-color: #1e1f20 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        padding: 4px 10px !important;
    }

    .stChatInputContainer:focus-within {
        border-color: #a855f7 !important;
        box-shadow: 0 0 15px rgba(168, 85, 247, 0.2) !important;
    }

    .gemini-badge {
        background: rgba(66, 133, 244, 0.15);
        color: #8ab4f8;
        border: 1px solid rgba(66, 133, 244, 0.3);
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
st.markdown(GEMINI_CUSTOM_CSS, unsafe_allow_html=True)


# ==========================================
# 5. INICIALIZACIÓN Y API KEY
# ==========================================
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

if "messages" not in st.session_state:
    st.session_state.messages = cargar_historial_db()

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

PREFERRED_MODELS = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"]


# ==========================================
# 6. FUNCIÓN DE GENERACIÓN CON FILES API
# ==========================================
def generate_gemini_response(contents):
    if not api_key:
        raise ValueError("No se ha configurado la clave API GEMINI_API_KEY en el archivo .env o en secrets.")

    genai.configure(api_key=api_key)
    last_error = None
    config = genai.types.GenerationConfig(temperature=0.1)

    for model_name in PREFERRED_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(contents, generation_config=config)
            return response.text, model_name
        except Exception as e:
            last_error = e
            continue

    # Fallback si los preferidos fallan
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in available:
            clean_name = m.replace("models/", "")
            if clean_name not in PREFERRED_MODELS:
                try:
                    model = genai.GenerativeModel(clean_name)
                    response = model.generate_content(contents, generation_config=config)
                    return response.text, clean_name
                except Exception as e:
                    last_error = e
                    continue
    except Exception:
        pass

    raise last_error if last_error else RuntimeError("No se pudo conectar con ningún modelo activo de Gemini.")


# ==========================================
# 7. SIDEBAR Y UI
# ==========================================
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; padding: 10px 0;">
        <div class="gemini-sparkle-icon">✨</div>
        <div>
            <h3 style="margin:0; font-size: 1.1rem; color: #e3e3e3;">Perseo AI Chat</h3>
            <span style="font-size: 0.75rem; color: #8e918f;">Soporte Técnico Especializado</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()

    if api_key:
        st.markdown('<div class="gemini-badge">🟢 Gemini AI Conectado</div>', unsafe_allow_html=True)
    else:
        st.error("🔴 Clave API no configurada")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📷 Adjuntar Captura de Pantalla")
    attached_image = st.file_uploader(
        "Sube una imagen del error en Perseo:",
        type=["jpg", "png", "jpeg"],
        help="El Asistente Gemini la analizará junto con tu mensaje"
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
    <h1 class="gemini-header-title">Hola, Soporte Perseo</h1>
    <p class="gemini-subtext">¿Con qué problema o código de error te puedo ayudar hoy?</p>
</div>
""", unsafe_allow_html=True)


# ==========================================
# 8. CHIPS DE SUGERENCIA Y RENDERIZADO DE MENSAJES
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
        if st.button("📊 Falta Cuenta Contable\n\n'No existe cuenta configurada'", key="chip3", use_container_width=True):
            st.session_state.pending_prompt = "Al intentar guardar la venta sale el error: 'Falta asignar cuenta contable para el grupo de producto SERVICIOS'."
            st.rerun()

    with col4:
        if st.button("🔢 Secuencia Duplicada\n\n'Número de comprobante duplicado'", key="chip4", use_container_width=True):
            st.session_state.pending_prompt = "El sistema muestra: 'Error de clave de acceso o secuencia de comprobante duplicada 001-002-00001234'."
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

for msg in st.session_state.messages:
    avatar = "✨" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        if "image" in msg and msg["image"] is not None:
            st.image(msg["image"], width=300)
        st.markdown(msg["content"])


# ==========================================
# 9. LÓGICA PRINCIPAL DE CHAT CONTEXTUAL MASIVO
# ==========================================
user_prompt = st.chat_input("Escribe tu consulta sobre Perseo PC o describe el error...")

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

    with st.chat_message("assistant", avatar="✨"):
        message_placeholder = st.empty()
        message_placeholder.markdown("*(Analizando codebase completo, estructura SQL y manuales con Gemini Pro...)*")

        try:
            # Construcción inteligente del contexto usando la Files API de Gemini
            contents = [SYSTEM_PROMPT]
            
            # 1. Inyectar base JSON local si existe
            kb_data = cargar_kb_json()
            if kb_data:
                contents.append(f"Base de conocimiento JSON local: {json.dumps(kb_data, ensure_ascii=False)}")

            # 2. Inyectar el archivo masivo repomix-output.txt mediante referencia de archivo remoto (Cero límites de tokens inline)
            remote_file = obtener_archivo_remoto_gemini(api_key)
            if remote_file:
                contents.append(remote_file)

            # 3. Inyectar historial de la conversación
            for past_msg in st.session_state.messages:
                role_label = "Usuario: " if past_msg["role"] == "user" else "Asistente Perseo: "
                contents.append(f"{role_label}{past_msg['content']}")

            # 4. Inyectar prompt de visión si hay imagen
            if image_preview is not None:
                prompt_con_vision = f"""
                Analiza minuciosamente esta captura de pantalla del sistema Perseo:
                1. Lee el código de error exacto de la ventana emergente.
                2. Identifica en qué pantalla de Perseo (PC, Web o Móvil) se encuentra el usuario.
                3. Consulta tu conocimiento y el código fuente completo adjunto y entrega la solución exacta.
                
                Consulta del usuario: {user_prompt}
                """
                contents.append(prompt_con_vision)
                contents.append(image_preview)

            response_text, model_used = generate_gemini_response(contents)
            message_placeholder.markdown(response_text)
            
            guardar_y_limpiar_mensaje("assistant", response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})

        except Exception as e:
            error_msg = f"**Error de conexión:** {str(e)}"
            message_placeholder.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
