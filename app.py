import os
import time
import base64
from PIL import Image
import streamlit as st
from dotenv import load_dotenv
import json
import google.generativeai as genai

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Perseo IA - Soporte Conversacional",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. DEFINICIÓN DEL SYSTEM PROMPT Y BASE DE CONOCIMIENTO
# ==========================================
SYSTEM_PROMPT = """
Eres 'Perseo AI Assistant Master', especialista senior en el ecosistema completo de Perseo ERP (Ecuador):
1. Perseo PC (Sistema de escritorio Windows)
2. Perseo Web (Plataforma en la Nube)
3. Perseo App Móvil (Android/iOS para vendedores y cobros)

REGLAS DE DIAGNÓSTICO Y RESPUESTA:
- Identifica siempre la plataforma afectada (PC, Web o Móvil). Si la consulta no lo especifica y la solución cambia según el entorno, responde indicando los pasos para Perseo PC y Perseo Web por separado.
- Proporciona la RUTA EXACTA DE MENÚ (Ejemplo en PC: 'Módulo Ventas > Transacciones > Facturación' / Ejemplo en Web: 'Menú Izquierdo > Comprobantes > Facturas').
- Para errores del SRI (Errores 500, clave de acceso duplicada, firma revocada, ambiente de pruebas vs producción), especifica la normativa vigente del SRI Ecuador y la solución técnica en el sistema.
- En la App Móvil, considera temas de sincronización offline, impresoras térmicas Bluetooth y configuración de IP/Servidor.

ESTRUCTURA DE RESPUESTA:
📍 **Plataforma Módulo:** [Indicar si es PC, Web o Móvil]
🛠️ **Paso a Paso en Interfaz:** [Ruta exacta de clics]
💡 **Causa Raíz / SRI:** [Explicación técnica del error]
"""

@st.cache_data
def cargar_base_conocimiento():
    try:
        with open("perseo_kb.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return json.dumps(data, ensure_ascii=False)
    except Exception:
        return ""

# Cargar el contexto y unirlo con el System Prompt principal
base_conocimiento_texto = cargar_base_conocimiento()
SYSTEM_PROMPT_COMPLETO = f"{SYSTEM_PROMPT}\n\nBASE DE DATOS TÉCNICA DE ERRORES PERSEO:\n{base_conocimiento_texto}"


# ==========================================
# 3. ESTILOS CSS
# ==========================================
GEMINI_CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Outfit:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Outfit', 'Google Sans', sans-serif;
    }

    /* Fondo general estilo Gemini Dark Mode */
    .stApp {
        background-color: #131314;
        color: #e3e3e3;
    }

    /* Ocultar menú de opciones predeterminado y pie de página de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Hacer el header transparente */
    header[data-testid="stHeader"] {
        background: transparent !important;
        z-index: 99999 !important;
    }

    /* Botón flotante para VOLVER A MOSTRAR el menú lateral */
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

    /* Sidebar Estilo Gemini Dark */
    section[data-testid="stSidebar"] {
        background-color: #1e1f20;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* Saludo Gemini Style Header */
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

    /* Tarjetas de sugerencia estilo Gemini Chips */
    .suggestion-card {
        background: #1e1f20;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        padding: 16px 20px;
        cursor: pointer;
        transition: all 0.25s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .suggestion-card:hover {
        background: #28292a;
        border-color: #4285f4;
        transform: translateY(-2px);
    }

    .suggestion-icon {
        font-size: 1.4rem;
        margin-bottom: 10px;
    }

    .suggestion-text {
        font-size: 0.9rem;
        color: #c4c7c5;
        font-weight: 500;
    }

    /* Mensajes del Chat Estilo Gemini */
    .stChatMessage {
        background-color: transparent !important;
        border: none !important;
        padding: 1rem 0rem !important;
    }

    /* Estilo para mensaje del Asistente Gemini */
    div[data-testid="stChatMessage"]:nth-child(even) {
        background-color: transparent !important;
    }

    /* Avatar e íconos */
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

    /* Caja de Input de Chat flotante */
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

    /* Badge de Estado */
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
# 4. INICIALIZACIÓN Y API KEY
# ==========================================
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

PREFERRED_MODELS = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]


# ==========================================
# 5. FUNCIÓN DE GENERACIÓN
# ==========================================
def generate_gemini_response(contents):
    """
    Intenta generar contenido probando secuencialmente modelos activos.
    """
    if not api_key:
        raise ValueError("No se ha configurado la clave API GEMINI_API_KEY en el archivo .env o en secrets.")

    genai.configure(api_key=api_key)
    last_error = None

    # 1. Probar modelos recomendados activos
    for model_name in PREFERRED_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(contents)
            return response.text, model_name
        except Exception as e:
            last_error = e
            continue

    # 2. Si fallan los preferidos, consultar modelos disponibles en la API
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in available:
            clean_name = m.replace("models/", "")
            if clean_name not in PREFERRED_MODELS:
                try:
                    model = genai.GenerativeModel(clean_name)
                    response = model.generate_content(contents)
                    return response.text, clean_name
                except Exception as e:
                    last_error = e
                    continue
    except Exception:
        pass

    raise last_error if last_error else RuntimeError("No se pudo conectar con ningún modelo activo de Gemini.")


# ==========================================
# 6. SIDEBAR Y UI
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
# 7. CHIPS DE SUGERENCIA Y RENDERIZADO DE MENSAJES
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

# Renderizar historial de mensajes
for msg in st.session_state.messages:
    avatar = "✨" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        if "image" in msg and msg["image"] is not None:
            st.image(msg["image"], width=300)
        st.markdown(msg["content"])


# ==========================================
# 8. LÓGICA PRINCIPAL DE CHAT
# ==========================================
user_prompt = st.chat_input("Escribe tu consulta sobre Perseo PC o describe el error...")

if st.session_state.pending_prompt and not user_prompt:
    user_prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if user_prompt:
    # 1. Agregar mensaje de usuario
    user_msg_data = {"role": "user", "content": user_prompt}
    if image_preview is not None:
        user_msg_data["image"] = image_preview

    st.session_state.messages.append(user_msg_data)

    with st.chat_message("user", avatar="👤"):
        if image_preview is not None:
            st.image(image_preview, width=300)
        st.markdown(user_prompt)

    # 2. Generar respuesta
    with st.chat_message("assistant", avatar="✨"):
        message_placeholder = st.empty()
        message_placeholder.markdown("*(Pensando y analizando caso en Perseo...)*")

        try:
            # Construir conversación usando el PROMPT COMPLETO (Base de Datos + Sistema)
            contents = [SYSTEM_PROMPT_COMPLETO]
            
            for past_msg in st.session_state.messages:
                role_label = "Usuario: " if past_msg["role"] == "user" else "Asistente Perseo: "
                contents.append(f"{role_label}{past_msg['content']}")

            # Instrucción e inyección de la imagen real para Gemini Vision
            if image_preview is not None:
                prompt_con_vision = f"""
                Analiza minuciosamente esta captura de pantalla del sistema Perseo:
                1. Lee el código de error exacto de la ventana emergente.
                2. Identifica en qué pantalla de Perseo (PC, Web o Móvil) se encuentra el usuario.
                3. Consulta tu conocimiento de Perseo y entrega la solución exacta para este error.
                
                Consulta del usuario: {user_prompt}
                """
                contents.append(prompt_con_vision)
                contents.append(image_preview) # <--- AQUÍ SE ENVÍA EL ARCHIVO AL MODELO

            response_text, model_used = generate_gemini_response(contents)
            message_placeholder.markdown(response_text)
            
            # Guardar respuesta
            st.session_state.messages.append({"role": "assistant", "content": response_text})

        except Exception as e:
            message_placeholder.error(f"❌ Error de comunicación con Gemini AI: {e}")
