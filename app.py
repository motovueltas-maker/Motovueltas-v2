import streamlit as st
import requests

# Configuración de página compacta
st.set_page_config(page_title="Calculadora Cambiaria", layout="wide", initial_sidebar_state="collapsed")

# --- CSS DE ULTRA-COMPACTACIÓN Y DISEÑO SÓLIDO ---
st.markdown("""
    <style>
        /* Reducción de espacios globales */
        .block-container { 
            padding-top: 0.2rem !important; 
            padding-bottom: 0.2rem !important; 
            padding-left: 0.3rem !important; 
            padding-right: 0.3rem !important; 
        }
        div[data-testid="stVerticalBlock"] > div { gap: 0.15rem !important; }
        
        /* Reducción de tamaño de texto e inputs */
        .stNumberInput label { 
            font-size: 0.75rem !important; 
            font-weight: 600 !important;
            margin-bottom: -4px !important;
        }
        .stNumberInput input { 
            font-size: 0.85rem !important; 
            padding: 0.25rem 0.4rem !important; 
            height: 2rem !important;
        }
        
        /* Ajuste fino de pestañas */
        .stTabs [data-baseweb="tab-list"] { gap: 4px !important; }
        .stTabs [data-baseweb="tab"] { 
            padding: 4px 8px !important; 
            font-size: 0.8rem !important; 
        }

        /* Estilo para las alertas/resultados reducidos */
        .stAlert {
            padding: 0.3rem 0.5rem !important;
            font-size: 0.85rem !important;
            margin-top: 0.2rem !important;
            margin-bottom: 0.2rem !important;
        }
        
        /* Reducción de margen en métricas */
        [data-testid="stMetricValue"] {
            font-size: 1.1rem !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.75rem !important;
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

# Tasa BCV Global Editable
tasa_bcv = st.number_input("Tasa BCV (Bs.):", value=tasa_api, step=0.01, format="%.4f")
tasa_intervencion = tasa_bcv * 1.005  # BCV + 0,5%

# Pestañas principales
tab1, tab2, tab3 = st.tabs(["⚡ Operativa", "📈 Utilidad", "💱 Conversión BCV"])

# ==========================================
# PESTAÑA 1: OPERATIVA RÁPIDA
# ==========================================
with tab1:
    col1, col2 = st.columns(2)

    with col1:
        usd_deseados = st.number_input("USD a comprar:", value=300.00, step=10.0)
        bs_necesarios = usd_deseados * tasa_intervencion
        st.info(f"**Requiere:** Bs. {bs_necesarios:,.2f}")

        usd_tarjeta = st.number_input("USD Tarjeta (BPAY):", value=500.64, step=10.0)
        comision_banco = st.number_input("% Com. Banco:", value=2.51, step=0.1) / 100
        usd_pasarela = (usd_tarjeta - 1.50) / (1 + comision_banco) if usd_tarjeta > 1.50 else 0.0
        st.success(f"**BPAY:** ${usd_pasarela:.2f}")

    with col2:
        bs_disponibles = st.number_input("Bs. dispongo:", value=80699.00, step=500.0)
        usd_obtenidos = bs_disponibles / tasa_intervencion
        st.info(f"**Obtiene:** ${usd_obtenidos:.2f}")

        bs_banco = st.number_input("Bs. en Banco:", value=216000.00, step=500.0)
        bs_transferir = bs_banco / 1.003
        st.success(f"**Transferir:** Bs. {bs_transferir:,.2f}")


# ==========================================
# PESTAÑA 2: CALCULADORA DE UTILIDAD
# ==========================================
with tab2:
    col_a, col_b = st.columns(2)

    with col_a:
        usd_comprados_banco = st.number_input("USD en Banco:", value=500.00, step=10.0, key="u_banco")
        comision_banco_u = st.number_input("% Com. Banco:", value=1.50, step=0.1, key="u_com_banco") / 100
        comision_bpay_u = st.number_input("% Pasarela BPay:", value=4.10, step=0.1, key="u_com_bpay") / 100

        bs_gastados_intervencion = usd_comprados_banco * tasa_intervencion
        st.info(f"**Inversión:** Bs. {bs_gastados_intervencion:,.2f}")

    with col_b:
        tasa_p2p = st.number_input("Tasa P2P (Bs.):", value=967.00, step=0.5, format="%.2f")

        usd_netos_tarjeta = (usd_comprados_banco - 1.50) / (1 + comision_banco_u) if usd_comprados_banco > 1.50 else 0.0
        usdt_recibidos = usd_netos_tarjeta * (1 - comision_bpay_u) if usd_netos_tarjeta > 0 else 0.0

        st.warning(f"**Binance:** {usdt_recibidos:.2f} USDT")

    bs_retorno_p2p = usdt_recibidos * tasa_p2p
    utilidad_bs = bs_retorno_p2p - bs_gastados_intervencion
    utilidad_usd_bcv = utilidad_bs / tasa_bcv if tasa_bcv > 0 else 0.0

    st.success(f"**Retorno Total:** Bs. {bs_retorno_p2p:,.2f}")
    
    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.metric(label="Utilidad (Bs.)", value=f"Bs. {utilidad_bs:,.2f}")
    with col_res2:
        st.metric(label="Utilidad (USD BCV)", value=f"${utilidad_usd_bcv:,.2f}")


# ==========================================
# PESTAÑA 3: CONVERSIÓN SIMPLE BCV
# ==========================================
with tab3:
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        usd_directo = st.number_input("Monto en USD:", value=100.00, step=10.0, key="conv_usd")
        bs_convertidos = usd_directo * tasa_bcv
        st.success(f"**Equivale a:**\nBs. {bs_convertidos:,.2f}")

    with col_c2:
        bs_directo = st.number_input("Monto en Bs.:", value=1000.00, step=100.0, key="conv_bs")
        usd_convertidos = bs_directo / tasa_bcv if tasa_bcv > 0 else 0.0
        st.info(f"**Equivale a:**\n${usd_convertidos:.2f} USD")
