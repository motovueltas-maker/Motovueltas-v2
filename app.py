import streamlit as st
import requests

# Configuración de página ultra-compacta
st.set_page_config(page_title="Calculadora Cambiaria", layout="wide", initial_sidebar_state="collapsed")

# --- CSS DE ULTRA-COMPACTACIÓN Y DISEÑO DE UNA SOLA PANTALLA ---
st.markdown("""
    <style>
        /* Reducción extrema de márgenes superiores y laterales */
        .block-container { 
            padding-top: 0.1rem !important; 
            padding-bottom: 0.1rem !important; 
            padding-left: 0.2rem !important; 
            padding-right: 0.2rem !important; 
        }
        div[data-testid="stVerticalBlock"] > div { gap: 0.05rem !important; }
        
        /* Reducción de fuentes e inputs */
        .stNumberInput label { 
            font-size: 0.65rem !important; 
            font-weight: 700 !important;
            margin-bottom: -6px !important;
            color: #333;
        }
        .stNumberInput input { 
            font-size: 0.75rem !important; 
            padding: 0.15rem 0.25rem !important; 
            height: 1.5rem !important;
            border-radius: 4px !important;
        }
        
        /* Ajuste de cajas de alertas y resultados */
        .stAlert {
            padding: 0.15rem 0.35rem !important;
            font-size: 0.72rem !important;
            margin-top: 0.1rem !important;
            margin-bottom: 0.1rem !important;
            border-radius: 4px !important;
        }

        /* Títulos de sección ultra-pequeños */
        .sub-header {
            font-size: 0.75rem !important;
            font-weight: 800;
            color: #1E3A8A;
            margin-top: 0.2rem !important;
            margin-bottom: 0.1rem !important;
            border-bottom: 1px solid #E5E7EB;
        }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIÓN TASA BCV AUTOMÁTICA ---
@st.cache_data(ttl=3600)
def obtener_tasa_bcv():
    try:
        url = "https://pydolarvenezuela-api.vercel.app/api/v1/dollar?page=bcv"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return float(data['monedas']['usd']['promedio'])
    except Exception:
        pass
    return 860.1753

tasa_api = obtener_tasa_bcv()

# --- TASA BCV GLOBAL ---
tasa_bcv = st.number_input("Tasa BCV (Bs.):", value=tasa_api, step=0.01, format="%.4f")
tasa_intervencion = tasa_bcv * 1.005  # BCV + 0,5%

# ==========================================
# BLOQUE 1: OPERATIVA RÁPIDA Y CONVERSIÓN BCV
# ==========================================
st.markdown('<div class="sub-header">⚡ OPERATIVA & CONVERSIÓN BCV</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    usd_deseados = st.number_input("USD a comprar:", value=300.00, step=10.0)
    bs_necesarios = usd_deseados * tasa_intervencion
    st.info(f"**Req:** Bs. {bs_necesarios:,.2f}")

    usd_tarjeta = st.number_input("USD Tarjeta (BPAY):", value=500.64, step=10.0)
    comision_banco = st.number_input("% Com. Banco:", value=2.51, step=0.1) / 100
    usd_pasarela = (usd_tarjeta - 1.50) / (1 + comision_banco) if usd_tarjeta > 1.50 else 0.0
    st.success(f"**BPAY:** ${usd_pasarela:.2f}")

    # Conversión BCV Directa: USD -> Bs
    usd_directo = st.number_input("USD (Conversión BCV):", value=100.00, step=10.0, key="c_usd")
    st.success(f"**Eq:** Bs. {(usd_directo * tasa_bcv):,.2f}")

with col2:
    bs_disponibles = st.number_input("Bs. dispongo:", value=80699.00, step=500.0)
    usd_obtenidos = bs_disponibles / tasa_intervencion
    st.info(f"**Obtiene:** ${usd_obtenidos:.2f}")

    bs_banco = st.number_input("Bs. en Banco:", value=216000.00, step=500.0)
    bs_transferir = bs_banco / 1.003
    st.success(f"**Transferir:** Bs. {bs_transferir:,.2f}")

    # Conversión BCV Directa: Bs -> USD
    bs_directo = st.number_input("Bs. (Conversión BCV):", value=1000.00, step=100.0, key="c_bs")
    st.info(f"**Eq:** ${(bs_directo / tasa_bcv if tasa_bcv > 0 else 0.0):.2f} USD")

# ==========================================
# BLOQUE 2: CALCULADORA DE UTILIDAD TOTAL
# ==========================================
st.markdown('<div class="sub-header">📈 UTILIDAD TOTAL P2P</div>', unsafe_allow_html=True)

col_a, col_b = st.columns(2)

with col_a:
    usd_comprados_banco = st.number_input("USD Banco:", value=500.00, step=10.0, key="u_banco")
    comision_banco_u = st.number_input("% Com. Banco origen:", value=1.50, step=0.1, key="u_com_b") / 100
    comision_bpay_u = st.number_input("% Pasarela BPay:", value=4.10, step=0.1, key="u_com_bp") / 100
    
    bs_gastados = usd_comprados_banco * tasa_intervencion
    st.info(f"**Inversión:** Bs. {bs_gastados:,.2f}")

with col_b:
    tasa_p2p = st.number_input("Tasa P2P (Bs.):", value=967.00, step=0.5, format="%.2f")

    usd_netos_tarjeta = (usd_comprados_banco - 1.50) / (1 + comision_banco_u) if usd_comprados_banco > 1.50 else 0.0
    usdt_recibidos = usd_netos_tarjeta * (1 - comision_bpay_u) if usd_netos_tarjeta > 0 else 0.0

    st.warning(f"**Binance:** {usdt_recibidos:.2f} USDT")

# Resultados Finales Compactos
bs_retorno_p2p = usdt_recibidos * tasa_p2p
utilidad_bs = bs_retorno_p2p - bs_gastados
utilidad_usd_bcv = utilidad_bs / tasa_bcv if tasa_bcv > 0 else 0.0

col_u1, col_u2 = st.columns(2)
with col_u1:
    st.success(f"**Ganancia:** Bs. {utilidad_bs:,.2f}")
with col_u2:
    st.success(f"**Ganancia:** ${utilidad_usd_bcv:,.2f} BCV")
    
