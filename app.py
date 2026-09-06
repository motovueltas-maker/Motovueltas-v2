import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime, date

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MotoVueltas v2", page_icon="🏍️", layout="wide")

# --- OCULTAR ELEMENTOS DE CABECERA (BOTÓN DE GITHUB Y MENÚS) ---
st.markdown("""
    <style>
    /* Oculta la barra superior de Streamlit y el botón de GitHub */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- CREDENCIALES GITHUB ---
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "motovueltas-maker/Motovueltas-v2")
BRANCH = "main"

FILE_MOTORIZADOS = "motorizados.csv"
FILE_CLIENTES = "clientes.csv"
FILE_USUARIOS = "usuarios.csv"
FILE_SERVICIOS = "servicios.csv"
FILE_AVANCES = "avances.csv"

headers_gh = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# --- FUNCIONES DE PERSISTENCIA GITHUB ---
def cargar_csv_desde_github(file_path):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}?ref={BRANCH}"
    r = requests.get(url, headers=headers_gh)
    if r.status_code == 200:
        content = base64.b64decode(r.json()['content']).decode('utf-8')
        from io import StringIO
        df = pd.read_csv(StringIO(content))
        df.columns = [c.strip().lower() for c in df.columns]
        return df, r.json()['sha']
    else:
        return pd.DataFrame(), None

def guardar_csv_en_github(file_path, df, sha_actual, mensaje_commit):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    csv_data = df.to_csv(index=False)
    encoded_content = base64.b64encode(csv_data.encode('utf-8')).decode('utf-8')
    data = {
        "message": mensaje_commit,
        "content": encoded_content,
        "branch": BRANCH
    }
    if sha_actual:
        data["sha"] = sha_actual
    r = requests.put(url, json=data, headers=headers_gh)
    return r.status_code in [200, 201]

# --- CONTROL DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario = ""
    st.session_state.rol = "Motorizado"

if not st.session_state.autenticado:
    st.title("🏍️ MotoVueltas - Acceso al Sistema")
    with st.form("form_login"):
        user_input = st.text_input("Usuario (ej: esneyder, omar)").strip().lower()
        pass_input = st.text_input("Contraseña", type="password").strip()
        btn_login = st.form_submit_button("Iniciar Sesión", type="primary")
        
        if btn_login:
            usuarios_validos = st.secrets.get("passwords", {})
            if user_input in usuarios_validos and str(usuarios_validos[user_input]) == pass_input:
                st.session_state.autenticado = True
                st.session_state.usuario = user_input
                st.session_state.rol = "Admin" if user_input == "esneyder" else "Motorizado"
                st.rerun()
            else:
                st.error("⚠️ Usuario o contraseña incorrectos.")
    st.stop()

# --- BARRA LATERAL (MENÚ Y PERFIL) ---
if "rol" not in st.session_state:
    st.session_state.rol = "Admin" if st.session_state.usuario == "esneyder" else "Motorizado"

st.sidebar.write(f"👤 **{st.session_state.usuario.capitalize()}** ({st.session_state.rol})")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

st.sidebar.markdown("---")

if st.session_state.get("rol", "Motorizado") == "Admin":
    opciones = [
        " Registrar Vuelta",
        " Validar Vueltas",
        " Corte Clientes",
        " Corte Motorizados",
        " Directorio Clientes",
        " Perfiles Motorizados"
    ]
else:
    opciones = [" Registrar Vuelta"]

opcion_menu = st.sidebar.radio("Módulo:", opciones)

# --- CARGA GENERAL DE DATOS ---
df_motos, sha_motos = cargar_csv_desde_github(FILE_MOTORIZADOS)
df_clientes, sha_clientes = cargar_csv_desde_github(FILE_CLIENTES)
df_servicios, sha_servicios = cargar_csv_desde_github(FILE_SERVICIOS)
df_avances, sha_avances = cargar_csv_desde_github(FILE_AVANCES)

if df_avances.empty:
    df_avances = pd.DataFrame(columns=['id', 'fecha', 'motorizado', 'monto', 'concepto', 'estado_avance'])
elif 'estado_avance' not in df_avances.columns:
    df_avances['estado_avance'] = 'Pendiente'

# --- MÓDULO: REGISTRAR VUELTA (COMPACTO) ---
if opcion_menu == " Registrar Vuelta":
    st.subheader("⚡ Registrar Nueva Vuelta / Carrera")
    
    if st.session_state.rol == "Admin":
        col_f1, col_f2, col_f3 = st.columns([1, 1, 1])
        with col_f1:
            fecha_fija = st.date_input("📅 Fecha", value=date.today())
        with col_f2:
            nom_motos = df_motos['nombre'].tolist() if not df_motos.empty else []
            mot_sel_fijo = st.selectbox("🏍️ Motorizado", nom_motos)
        with col_f3:
            com_def = 66.67
            if not df_motos.empty and mot_sel_fijo in df_motos['nombre'].values:
                com_def = float(df_motos[df_motos['nombre'] == mot_sel_fijo]['porcentaje_ganancia'].values[0])
            comision_fija = st.number_input("% Ganancia Moto", min_value=0.0, max_value=100.0, value=com_def, step=0.5)
    else:
        col_f1, _ = st.columns([1, 2])
        with col_f1:
            fecha_fija = st.date_input("📅 Fecha", value=date.today())
        mot_sel_fijo = st.session_state.usuario.capitalize()
        comision_fija = 66.67
        if not df_motos.empty and mot_sel_fijo in df_motos['nombre'].values:
            comision_fija = float(df_motos[df_motos['nombre'] == mot_sel_fijo]['porcentaje_ganancia'].values[0])
            
    fecha_str = fecha_fija.strftime("%Y-%m-%d")

    with st.form("form_nueva_vuelta_compacta", clear_on_submit=True):
        nom_clientes = df_clientes['nombre'].tolist() if not df_clientes.empty else []
        cli_sel = st.selectbox("Cliente *", nom_clientes, index=None, placeholder="Selecciona un cliente...")
        
        if st.session_state.rol == "Admin":
            c_orig, c_dest, c_prec = st.columns([1, 1, 1])
            with c_orig:
                origen = st.text_input("Desde", placeholder="Local")
            with c_dest:
                destino = st.text_input("Hasta", placeholder="Local")
            with c_prec:
                precio_ingresado = st.number_input("Precio ($) *", min_value=0.0, step=0.5, value=0.0)
        else:
            c_orig, c_dest = st.columns(2)
            with c_orig:
                origen = st.text_input("Desde", placeholder="Local")
            with c_dest:
                destino = st.text_input("Hasta", placeholder="Local")
            precio_ingresado = 0.0

        btn_guardar = st.form_submit_button("🚀 Precargar / Registrar Vuelta", type="primary", use_container_width=True)
        
        if btn_guardar:
            if not cli_sel:
                st.error("⚠️ Debes seleccionar un cliente de la lista.")
            elif st.session_state.rol == "Admin" and precio_ingresado <= 0:
                st.error("⚠️ Por favor ingresa un precio válido mayor a 0.")
            else:
                nuevo_id = len(df_servicios) + 1 if not df_servicios.empty else 1
                hora_actual = datetime.now().strftime("%H:%M")
                fecha_completa = f"{fecha_str} {hora_actual}"
                
                if st.session_state.rol == "Admin":
                    est_val = "Validado"
                    precio_val = float(precio_ingresado)
                    monto_mot = round(precio_val * (comision_fija / 100.0), 2)
                    monto_emp = round(precio_val - monto_mot, 2)
                else:
                    est_val = "Pendiente"
                    precio_val = 0.0
                    monto_mot = 0.0
                    monto_emp = 0.0

                nueva_fila = pd.DataFrame([{
                    "id": nuevo_id,
                    "fecha": fecha_completa,
                    "motorizado": mot_sel_fijo,
                    "cliente": cli_sel,
                    "origen": origen if origen else "Local",
                    "destino": destino if destino else "Local",
                    "detalle": "",
                    "precio_cliente": precio_val,
                    "porcentaje_comision": comision_fija,
                    "monto_motorizado": monto_mot,
                    "ganancia_empresa": monto_emp,
                    "estado_validacion": est_val,
                    "estado_cliente": "Pendiente",
                    "estado_motorizado": "Pendiente"
                }])
                
                df_servicios = pd.concat([df_servicios, nueva_fila], ignore_index=True)
                if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, f"Vuelta #{nuevo_id} cargada por {st.session_state.usuario}"):
                    st.success(f"✅ Vuelta #{nuevo_id} guardada exitosamente ({est_val}).")
                    st.rerun()
                else:
                    st.error("❌ Error al guardar los datos en GitHub.")

# --- MÓDULO: VALIDAR VUELTAS (Solo Admin) ---
elif opcion_menu == " Validar Vueltas":
    st.header("⚙️ Validar y Asignar Precios")
    if not df_servicios.empty:
        pendientes = df_servicios[df_servicios['estado_validacion'] == "Pendiente"]
        if pendientes.empty:
            st.info("No hay vueltas pendientes por validar.")
        else:
            for idx, row in pendientes.iterrows():
                with st.expander(f"Vuelta #{row['id']} - {row['motorizado']} ({row['cliente']}) - Fecha: {row['fecha']}"):
                    st.write(f"**Ruta:** {row['origen']} ➡️ {row['destino']}")
                    c1, c2 = st.columns(2)
                    with c1:
                        precio = st.number_input(f"Precio Cliente ($) #{row['id']}", min_value=0.0, value=float(row['precio_cliente']), step=0.5)
                    with c2:
                        com_def = 66.67
                        if not df_motos.empty and row['motorizado'] in df_motos['nombre'].values:
                            com_def = float(df_motos[df_motos['nombre'] == row['motorizado']]['porcentaje_ganancia'].values[0])
                        comision = st.number_input(f"% Ganancia Motorizado #{row['id']}", min_value=0.0, max_value=100.0, value=com_def)
                    
                    if st.button(f"Confirmar y Validar #{row['id']}", type="primary"):
                        monto_mot = round(precio * (comision / 100.0), 2)
                        monto_emp = round(precio - monto_mot, 2)
                        df_servicios.at[idx, 'precio_cliente'] = precio
                        df_servicios.at[idx, 'porcentaje_comision'] = comision
                        df_servicios.at[idx, 'monto_motorizado'] = monto_mot
                        df_servicios.at[idx, 'ganancia_empresa'] = monto_emp
                        df_servicios.at[idx, 'estado_validacion'] = "Validado"
                        if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, f"Validada vuelta #{row['id']}"):
                            st.success(f"Vuelta #{row['id']} validada correctamente.")
                            st.rerun()

# --- MÓDULO: DIRECTORIO CLIENTES ---
elif opcion_menu == " Directorio Clientes":
    st.header("👥 Gestión y Directorio de Clientes")
    col_c1, col_c2 = st.columns([1, 1])
    
    with col_c1:
        st.subheader("➕ Agregar Nuevo Cliente")
        with st.form("form_agregar_cliente", clear_on_submit=True):
            tel_c = st.text_input("Teléfono / WhatsApp (ID Único) *").strip()
            nom_c = st.text_input("Nombre / Negocio *").strip()
            ubi_c = st.text_input("Ubicación Principal *").strip()
            btn_guardar_c = st.form_submit_button("Guardar Cliente", type="primary", use_container_width=True)
            if btn_guardar_c:
                if not tel_c or not nom_c:
                    st.error("⚠️ El teléfono y el nombre son obligatorios.")
                elif not df_clientes.empty and tel_c in df_clientes['telefono'].astype(str).values:
                    st.error(f"⚠️ El número {tel_c} ya pertenece a un cliente registrado.")
                else:
                    nueva_c = pd.DataFrame([{"id": tel_c, "nombre": nom_c, "telefono": tel_c, "ubicacion": ubi_c if ubi_c else "Local", "saldo_pendiente": 0.0}])
                    df_clientes = pd.concat([df_clientes, nueva_c], ignore_index=True)
                    if guardar_csv_en_github(FILE_CLIENTES, df_clientes, sha_clientes, f"Nuevo cliente {nom_c}"):
                        st.success(f"✅ Cliente '{nom_c}' agregado exitosamente.")
                        st.rerun()

    with col_c2:
        st.subheader("✏️ Editar Cliente Existente")
        nom_clientes_lista = df_clientes['nombre'].tolist() if not df_clientes.empty else []
        cliente_a_editar = st.selectbox("Seleccionar Cliente a Modificar", nom_clientes_lista, index=None, placeholder="Buscar o seleccionar cliente...")
        if cliente_a_editar:
            datos_actuales = df_clientes[df_clientes['nombre'] == cliente_a_editar].iloc[0]
            with st.form("form_editar_cliente"):
                st.info(f"📱 Teléfono / ID: **{datos_actuales['telefono']}** (No editable)")
                nuevo_nombre = st.text_input("Nombre / Negocio", value=str(datos_actuales['nombre']))
                nueva_ubicacion = st.text_input("Ubicación", value=str(datos_actuales['ubicacion']))
                btn_actualizar = st.form_submit_button("Actualizar Datos", type="primary", use_container_width=True)
                if btn_actualizar:
                    idx_edit = df_clientes[df_clientes['nombre'] == cliente_a_editar].index[0]
                    df_clientes.at[idx_edit, 'nombre'] = nuevo_nombre.strip()
                    df_clientes.at[idx_edit, 'ubicacion'] = nueva_ubicacion.strip()
                    if guardar_csv_en_github(FILE_CLIENTES, df_clientes, sha_clientes, f"Actualizado cliente {nuevo_nombre}"):
                        st.success(f"✅ Datos de '{nuevo_nombre}' actualizados correctamente.")
                        st.rerun()

    st.markdown("---")
    st.subheader("📋 Lista de Clientes Registrados")
    if not df_clientes.empty:
        df_mostrar = df_clientes[['nombre', 'telefono', 'ubicacion']].copy()
        df_mostrar.columns = ["Nombre / Negocio", "Teléfono / WhatsApp", "Ubicación"]
        st.dataframe(df_mostrar, use_container_width=True)
    else:
        st.info("No hay clientes registrados en la base de datos.")

# --- MÓDULO: PERFILES MOTORIZADOS ---
elif opcion_menu == " Perfiles Motorizados":
    st.header("🏍️ Gestión de Motorizados")
    if not df_motos.empty:
        st.dataframe(df_motos, use_container_width=True)
    with st.form("form_agregar_moto", clear_on_submit=True):
        st.subheader("➕ Agregar Motorizado")
        nom_m = st.text_input("Nombre del Chofer")
        tel_m = st.text_input("Teléfono")
        com_m = st.number_input("% Ganancia Base", value=66.67)
        if st.form_submit_button("Guardar Motorizado") and nom_m:
            nuevo_id_m = len(df_motos) + 1 if not df_motos.empty else 1
            nueva_m = pd.DataFrame([{"id": nuevo_id_m, "nombre": nom_m, "telefono": tel_m, "porcentaje_ganancia": com_m, "saldo_pendiente": 0.0}])
            df_motos = pd.concat([df_motos, nueva_m], ignore_index=True)
            guardar_csv_en_github(FILE_MOTORIZADOS, df_motos, sha_motos, f"Nuevo motorizado {nom_m}")

# --- MÓDULO: CORTE CLIENTES Y GESTIÓN DE VUELTAS ---
elif "Corte Clientes" in opcion_menu or "Cuentas" in opcion_menu:
    st.subheader("📊 Balance y Corte de Cuentas - Clientes")
    nom_clientes = df_clientes['nombre'].tolist() if not df_clientes.empty else []
    if not df_servicios.empty and nom_clientes:
        tab_balance, tab_gestion = st.tabs(["💰 Balance de Cuenta", "✏️ Editar / Eliminar Vueltas"])
        
        with tab_balance:
            cliente_sel = st.selectbox("Seleccionar Cliente para ver Balance:", nom_clientes, index=0)
            df_cli_all = df_servicios[df_servicios['cliente'].astype(str).str.strip().str.lower() == str(cliente_sel).strip().lower()].copy()
            
            st.markdown("##### 📅 Filtrar Reporte por Fechas")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                f_desde_c = st.date_input("Fecha Desde (Opcional):", value=None, format="DD/MM/YYYY", key="f_desde_corte")
            with col_f2:
                f_hasta_c = st.date_input("Fecha Hasta (Opcional):", value=None, format="DD/MM/YYYY", key="f_hasta_corte")

            fechas_cli_str = pd.to_datetime(df_cli_all['fecha'], errors='coerce').dt.strftime('%Y-%m-%d')
            if f_desde_c and f_hasta_c:
                pendientes = df_cli_all[(fechas_cli_str >= f_desde_c.strftime('%Y-%m-%d')) & (fechas_cli_str <= f_hasta_c.strftime('%Y-%m-%d'))].copy()
            elif f_desde_c:
                pendientes = df_cli_all[fechas_cli_str == f_desde_c.strftime('%Y-%m-%d')].copy()
            elif f_hasta_c:
                pendientes = df_cli_all[fechas_cli_str == f_hasta_c.strftime('%Y-%m-%d')].copy()
            else:
                pendientes = df_cli_all[df_cli_all['estado_cliente'] == 'Pendiente'].copy()

            def formatear_dd_mm(val):
                if pd.isna(val) or not str(val).strip() or str(val).lower() == 'none': return ""
                try:
                    dt = pd.to_datetime(val, errors='coerce')
                    if pd.notnull(dt): return dt.strftime('%d/%m')
                    parts = str(val)[:10].split('-')
                    if len(parts) == 3: return f"{parts[2]}/{parts[1]}"
                    return str(val)[:5]
                except: return str(val)[:5]

            pendientes['fecha_corta'] = pendientes['fecha'].apply(formatear_dd_mm)
            total_deuda = pendientes['precio_cliente'].astype(float).sum()

            c_m1, c_m2 = st.columns(2)
            c_m1.metric("Pendiente por Cobrar ($)", f"${total_deuda:.2f}")
            c_m2.metric("Vueltas Filtradas / Pendientes", len(pendientes))
            st.markdown("---")

            col_abono, col_wa = st.columns([2, 1])
            with col_abono:
                abono_cliente = st.number_input("💵 Registrar Abono / Descuento ($):", min_value=0.0, max_value=float(total_deuda) if total_deuda > 0 else 0.0, value=0.0, step=0.5)
                tel_cliente = ""
                if not df_clientes.empty and 'telefono' in df_clientes.columns:
                    c_info = df_clientes[df_clientes['nombre'].astype(str).str.strip().str.lower() == str(cliente_sel).strip().lower()]
                    if not c_info.empty:
                        tel_cliente = str(c_info.iloc[0]['telefono']).replace("+", "").replace(" ", "").replace("-", "")
            with col_wa:
                st.write("")
                st.write("")
                if tel_cliente:
                    st.link_button("📲 Abrir Chat WhatsApp", f"https://wa.me/{tel_cliente}", use_container_width=True)
                else:
                    st.caption("⚠️ Cliente sin teléfono registrado")

            st.markdown("### 📋 Detalle de Servicios")
            if not pendientes.empty:
                st.dataframe(pendientes[['id', 'fecha_corta', 'motorizado', 'origen', 'destino', 'precio_cliente', 'estado_cliente']], use_container_width=True)

            total_neto = max(0.0, total_deuda - abono_cliente)
            msg_whatsapp = f"🧾 *REPORTE DE CUENTA - MOTOVUELTAS*\nCliente: *{cliente_sel}*\n\n"
            for f_corta in pendientes['fecha_corta'].unique():
                if f_corta:
                    msg_whatsapp += f"📅 *{f_corta}*\n"
                    for _, r in pendientes[pendientes['fecha_corta'] == f_corta].iterrows():
                        msg_whatsapp += f"▪ {r['origen']} ➡️ {r['destino']} = *${float(r['precio_cliente']):.2f}*\n"
                    msg_whatsapp += "\n"
            msg_whatsapp += "───────────────\n"
            msg_whatsapp += f"💵 *Subtotal Vueltas:* ${total_deuda:.2f}\n"
            if abono_cliente > 0:
                msg_whatsapp += f"📉 *Abono Registrado:* -${abono_cliente:.2f}\n"
            msg_whatsapp += f"💰 *TOTAL A PAGAR: ${total_neto:.2f}*"

            st.markdown("📱 **Mensaje de Control para WhatsApp:**")
            st.code(msg_whatsapp, language="text")
            st.markdown("---")

            confirmar_pago = st.checkbox(f"⚠️ Confirmar que deseas marcar estas {len(pendientes)} vueltas como PAGADAS.", key="check_pago_seguro")
            if st.button(f"✅ Marcar todas estas vueltas de {cliente_sel} como PAGADAS", type="primary", disabled=not confirmar_pago, use_container_width=True):
                ids_a_pagar = pendientes['id'].tolist()
                df_servicios.loc[df_servicios['id'].isin(ids_a_pagar), 'estado_cliente'] = 'Pagado'
                if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, f"Liquidacion de vueltas para {cliente_sel}"):
                    st.success(f"✅ ¡Se han marcado {len(ids_a_pagar)} vueltas de {cliente_sel} como PAGADAS correctamente!")
                    st.rerun()

        with tab_gestion:
            st.markdown("##### 🔎 Buscar y Modificar Vueltas")
            if not df_servicios.empty:
                col_f1, col_f2, col_f3, col_f4 = st.columns([1.5, 1.5, 1.5, 1.5])
                nom_motos_l = df_motos['nombre'].tolist() if not df_motos.empty else []
                nom_cli_l = df_clientes['nombre'].tolist() if not df_clientes.empty else []
                with col_f1:
                    filtro_cli = st.selectbox("Cliente:", ["Todos"] + nom_cli_l, index=0, key="f_cli_tab2")
                with col_f2:
                    filtro_mot = st.selectbox("Motorizado:", ["Todos"] + nom_motos_l, index=0, key="f_mot_tab2")
                with col_f3:
                    f_desde = st.date_input("Fecha Desde (Opcional):", value=None, format="DD/MM/YYYY", key="fd_tab2")
                with col_f4:
                    f_hasta = st.date_input("Fecha Hasta (Opcional):", value=None, format="DD/MM/YYYY", key="fh_tab2")

                df_filtrado = df_servicios.copy()

                # Convertir la columna fecha soportando formatos DD/MM/YYYY y YYYY-MM-DD
                fechas_dt = pd.to_datetime(df_filtrado['fecha'], dayfirst=True, errors='coerce')
                fechas_str = fechas_dt.dt.strftime('%Y-%m-%d').fillna(df_filtrado['fecha'].astype(str).str[:10])

                if f_desde and f_hasta:
                    df_filtrado = df_filtrado[(fechas_str >= f_desde.strftime('%Y-%m-%d')) & (fechas_str <= f_hasta.strftime('%Y-%m-%d'))]
                elif f_desde:
                    df_filtrado = df_filtrado[fechas_str == f_desde.strftime('%Y-%m-%d')]
                elif f_hasta:
                    df_filtrado = df_filtrado[fechas_str == f_hasta.strftime('%Y-%m-%d')]

                if filtro_cli and filtro_cli != "Todos":
                    df_filtrado = df_filtrado[df_filtrado['cliente'].astype(str).str.strip().str.lower() == filtro_cli.strip().lower()]
                if filtro_mot and filtro_mot != "Todos":
                    df_filtrado = df_filtrado[df_filtrado['motorizado'].astype(str).str.strip().str.lower() == filtro_mot.strip().lower()]

                df_filtrado['fecha_real'] = pd.to_datetime(df_filtrado['fecha'], errors='coerce').dt.strftime('%Y-%m-%d')
                df_filtrado['eliminar'] = False
                st.markdown(f"**Vueltas encontradas:** {len(df_filtrado)}")

                if not df_filtrado.empty:
                    column_config = {
                        "eliminar": st.column_config.CheckboxColumn("🗑️ Borrar", default=False),
                        "id": st.column_config.NumberColumn("ID", disabled=True),
                        "fecha_real": st.column_config.TextColumn("Fecha (AAAA-MM-DD)", help="Ejemplo: 2026-08-07"),
                        "cliente": st.column_config.SelectboxColumn("Cliente", options=nom_cli_l, required=True),
                        "motorizado": st.column_config.SelectboxColumn("Motorizado", options=nom_motos_l, required=True),
                        "origen": st.column_config.TextColumn("Desde"),
                        "destino": st.column_config.TextColumn("Hasta"),
                        "precio_cliente": st.column_config.NumberColumn("Precio ($)", format="$%.2f", min_value=0.0, step=0.5),
                        "estado_cliente": st.column_config.SelectboxColumn("Estado Pago", options=["Pendiente", "Pagado"])
                    }
                    column_order = ["eliminar", "id", "fecha_real", "cliente", "motorizado", "origen", "destino", "precio_cliente", "estado_cliente"]
                    df_editado = st.data_editor(df_filtrado[column_order], column_config=column_config, use_container_width=True, hide_index=True, key="editor_tabla_vueltas_interactivo")

                    if st.button("💾 Guardar Cambios Realizados en la Tabla", type="primary", use_container_width=True):
                        filas_eliminar = df_editado[df_editado['eliminar'] == True]['id'].tolist()
                        if filas_eliminar:
                            df_servicios = df_servicios[~df_servicios['id'].isin(filas_eliminar)].reset_index(drop=True)

                        filas_modificadas = df_editado[df_editado['eliminar'] == False]
                        for _, row in filas_modificadas.iterrows():
                            id_v = row['id']
                            idx_orig = df_servicios[df_servicios['id'] == id_v].index
                            if not idx_orig.empty:
                                i = idx_orig[0]
                                fecha_editada = str(row['fecha_real']).strip()
                                if len(fecha_editada) == 10: 
                                    fecha_editada += " 12:00"
                                df_servicios.at[i, 'fecha'] = fecha_editada
                                df_servicios.at[i, 'cliente'] = row['cliente']
                                df_servicios.at[i, 'motorizado'] = row['motorizado']
                                df_servicios.at[i, 'origen'] = row['origen']
                                df_servicios.at[i, 'destino'] = row['destino']
                                df_servicios.at[i, 'precio_cliente'] = row['precio_cliente']
                                df_servicios.at[i, 'estado_cliente'] = row['estado_cliente']

                                comision = 66.67
                                if not df_motos.empty and 'porcentaje_ganancia' in df_motos.columns:
                                    m_data = df_motos[df_motos['nombre'].astype(str).str.strip().str.lower() == str(row['motorizado']).strip().lower()]
                                    if not m_data.empty: 
                                        comision = float(m_data.iloc[0]['porcentaje_ganancia'])
                                precio = float(row['precio_cliente'])
                                m_mot = round(precio * (comision / 100.0), 2)
                                m_emp = round(precio - m_mot, 2)
                                df_servicios.at[i, 'porcentaje_comision'] = comision
                                df_servicios.at[i, 'monto_motorizado'] = m_mot
                                df_servicios.at[i, 'ganancia_empresa'] = m_emp

                        if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, "Edicion de fecha real y datos de vueltas"):
                            st.success("✅ ¡Cambios guardados correctamente!")
                            st.rerun()
            else:
                st.info("No hay servicios registrados.")
    else:
        st.info("No hay servicios registrados en la base de datos.")

# --- MÓDULO: CORTE MOTORIZADOS ---
elif opcion_menu == " Corte Motorizados":
    st.subheader("🏍️ Balance y Corte de Cuentas - Motorizados")
    nom_motos = df_motos['nombre'].tolist() if not df_motos.empty else []
    
    if not df_servicios.empty and nom_motos:
        moto_sel = st.selectbox("Seleccionar Motorizado para ver Balance:", nom_motos, index=0)
        
        # 1. FILTRO DE FECHAS Y ESTADO
        st.markdown("##### 📅 Filtrar por Rango de Fechas")
        col_fm1, col_fm2, col_fm3 = st.columns([1, 1, 1])
        with col_fm1:
            f_desde_m = st.date_input("Fecha Desde (Opcional):", value=None, format="DD/MM/YYYY", key="fd_moto")
        with col_fm2:
            f_hasta_m = st.date_input("Fecha Hasta (Opcional):", value=None, format="DD/MM/YYYY", key="fh_moto")
        with col_fm3:
            estado_filtro_m = st.selectbox("Estado de Vueltas:", ["Pendientes", "Pagadas", "Todas"], index=0)

        # Filtrar vueltas del motorizado
        df_mot_serv = df_servicios[(df_servicios['motorizado'].astype(str).str.strip().str.lower() == str(moto_sel).strip().lower())].copy()
        
        fechas_mot_dt = pd.to_datetime(df_mot_serv['fecha'], dayfirst=True, errors='coerce')
        fechas_mot_str = fechas_mot_dt.dt.strftime('%Y-%m-%d').fillna(df_mot_serv['fecha'].astype(str).str[:10])

        if f_desde_m and f_hasta_m:
            df_mot_serv = df_mot_serv[(fechas_mot_str >= f_desde_m.strftime('%Y-%m-%d')) & (fechas_mot_str <= f_hasta_m.strftime('%Y-%m-%d'))]
        elif f_desde_m:
            df_mot_serv = df_mot_serv[fechas_mot_str == f_desde_m.strftime('%Y-%m-%d')]
        elif f_hasta_m:
            df_mot_serv = df_mot_serv[fechas_mot_str == f_hasta_m.strftime('%Y-%m-%d')]

        if estado_filtro_m == "Pendientes":
            vueltas_mo = df_mot_serv[df_mot_serv['estado_motorizado'] == 'Pendiente'].copy()
        elif estado_filtro_m == "Pagadas":
            vueltas_mo = df_mot_serv[df_mot_serv['estado_motorizado'] == 'Pagado'].copy()
        else:
            vueltas_mo = df_mot_serv.copy()

        def formatear_dd_mm(val):
            if pd.isna(val) or not str(val).strip() or str(val).lower() == 'none': return ""
            try:
                dt = pd.to_datetime(val, dayfirst=True, errors='coerce')
                if pd.notnull(dt): return dt.strftime('%d/%m')
                parts = str(val)[:10].split('-')
                if len(parts) == 3: return f"{parts[2]}/{parts[1]}"
                return str(val)[:5]
            except: return str(val)[:5]

        vueltas_mo['fecha_corta'] = vueltas_mo['fecha'].apply(formatear_dd_mm)
        total_comision = vueltas_mo['monto_motorizado'].astype(float).sum()

        # 2. FORMULARIO Y GUARDADO PERMANENTE DE AVANCES EN GITHUB
        with st.expander("💵 Registrar Avance / Adelanto de Dinero"):
            with st.form("form_avance_motorizado", clear_on_submit=True):
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    f_avance = st.date_input("Fecha Avance", value=date.today())
                with col_a2:
                    monto_avance = st.number_input("Monto Avance ($)", min_value=0.0, step=0.5)
                concepto_avance = st.text_input("Concepto / Nota (ej: Gasolina, Almuerzo)", placeholder="Detalle del avance...")
                btn_avance = st.form_submit_button("Guardar Avance Permanente", type="primary")
                
                if btn_avance and monto_avance > 0:
                    nuevo_av = pd.DataFrame([{
                        "id": nuevo_id,
                        "fecha": f_avance.strftime("%Y-%m-%d"),
                        "motorizado": str(moto_sel).strip(),
                        "monto": float(monto_avance),
                        "concepto": concepto_avance if concepto_avance else "Adelanto de dinero",
                        "estado_avance": "Pendiente"
                    }])
                    df_avances_act = pd.concat([df_avances, nuevo_av], ignore_index=True)
                    if guardar_csv_en_github(FILE_AVANCES, df_avances_act, sha_avances, f"Nuevo avance a {moto_sel}"):
                        st.success(f"✅ Avance de ${monto_avance:.2f} guardado permanentemente en GitHub.")
                        st.rerun()

        # 3. CARGA DE AVANCES PERMANENTES FILTRADOS POR FECHA
        df_avances_moto = df_avances[(df_avances['motorizado'].astype(str).str.strip().str.lower() == str(moto_sel).strip().lower())].copy() if not df_avances.empty else pd.DataFrame()
        
        if not df_avances_moto.empty:
            # Convertir cualquier formato de fecha a YYYY-MM-DD
            av_dt = pd.to_datetime(df_avances_moto['fecha'], errors='coerce')
            av_str = av_dt.dt.strftime('%Y-%m-%d').fillna(df_avances_moto['fecha'].astype(str).str[:10])

            if f_desde_m and f_hasta_m:
                df_avances_moto = df_avances_moto[(av_str >= f_desde_m.strftime('%Y-%m-%d')) & (av_str <= f_hasta_m.strftime('%Y-%m-%d'))]
            elif f_desde_m:
                df_avances_moto = df_avances_moto[av_str == f_desde_m.strftime('%Y-%m-%d')]
            elif f_hasta_m:
                df_avances_moto = df_avances_moto[av_str <= f_hasta_m.strftime('%Y-%m-%d')]

            df_avances_moto['fecha_corta'] = df_avances_moto['fecha'].apply(formatear_dd_mm)
            total_avances = df_avances_moto['monto'].astype(float).sum()
        else:
            total_avances = 0.0

        saldo_neto_pagar = total_comision - total_avances

        # 4. MÉTRICAS PRINCIPALES
        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
        c_m1.metric("Comisiones Ganadas", f"${total_comision:.2f}")
        c_m2.metric("Adelantos Registrados", f"-${total_avances:.2f}")
        c_m3.metric("🔥 Saldo Neto a Pagar", f"${saldo_neto_pagar:.2f}")
        c_m4.metric("Vueltas Encontradas", len(vueltas_mo))

        # 5. TABLA VISUAL DE ADELANTOS REGISTRADOS EN GITHUB
        if not df_avances_moto.empty:
            st.markdown("##### 💵 Adelantos / Avances Registrados en el Periodo (GitHub)")
            st.dataframe(df_avances_moto[['fecha_corta', 'monto', 'concepto']].rename(columns={
                'fecha_corta': 'Fecha',
                'monto': 'Monto ($)',
                'concepto': 'Concepto'
            }), use_container_width=True)

        st.markdown("---")

        # 6. DETALLE DE VUELTAS EDITABLE Y MENSAJE DE WHATSAPP
        st.markdown("### 📋 Detalle de Vueltas (Editable)")
        if not vueltas_mo.empty:
            # Seleccionar columnas para edición segura
            cols_editables = ['id', 'fecha_corta', 'cliente', 'origen', 'destino', 'precio_cliente', 'porcentaje_comision', 'monto_motorizado', 'estado_motorizado']
            
            # Asegurar columnas numéricas
            vueltas_mo['porcentaje_comision'] = pd.to_numeric(vueltas_mo['porcentaje_comision'], errors='coerce').fillna(66.67)
            vueltas_mo['monto_motorizado'] = pd.to_numeric(vueltas_mo['monto_motorizado'], errors='coerce').fillna(0.0)
            vueltas_mo['precio_cliente'] = pd.to_numeric(vueltas_mo['precio_cliente'], errors='coerce').fillna(0.0)

            column_config_m = {
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "fecha_corta": st.column_config.TextColumn("Fecha", disabled=True),
                "cliente": st.column_config.TextColumn("Cliente", disabled=True),
                "origen": st.column_config.TextColumn("Desde", disabled=True),
                "destino": st.column_config.TextColumn("Hasta", disabled=True),
                "precio_cliente": st.column_config.NumberColumn("Precio Cliente ($)", format="$%.2f", step=0.5),
                "porcentaje_comision": st.column_config.NumberColumn("% Ganancia Moto", min_value=0.0, max_value=100.0, step=0.5, format="%.1f%%"),
                "monto_motorizado": st.column_config.NumberColumn("Monto Motorizado ($)", format="$%.2f", step=0.1),
                "estado_motorizado": st.column_config.SelectboxColumn("Estado Pago", options=["Pendiente", "Pagado"])
            }

            vueltas_editadas = st.data_editor(
                vueltas_mo[cols_editables],
                column_config=column_config_m,
                use_container_width=True,
                hide_index=True,
                key=f"editor_vueltas_{moto_sel}"
            )

            # Botón para recalcular y guardar cambios en las vueltas editadas
            if st.button("💾 Guardar Cambios Realizados en Vueltas", type="secondary", use_container_width=True):
                for _, r_edit in vueltas_editadas.iterrows():
                    idx_v = df_servicios[df_servicios['id'] == r_edit['id']].index
                    if not idx_v.empty:
                        i = idx_v[0]
                        precio_act = float(r_edit['precio_cliente'])
                        com_act = float(r_edit['porcentaje_comision'])
                        
                        # Si cambió el precio o el porcentaje, recalcular monto
                        monto_act = float(r_edit['monto_motorizado'])
                        if com_act != float(df_servicios.at[i, 'porcentaje_comision']) or precio_act != float(df_servicios.at[i, 'precio_cliente']):
                            monto_act = round(precio_act * (com_act / 100.0), 2)

                        df_servicios.at[i, 'precio_cliente'] = precio_act
                        df_servicios.at[i, 'porcentaje_comision'] = com_act
                        df_servicios.at[i, 'monto_motorizado'] = monto_act
                        df_servicios.at[i, 'ganancia_empresa'] = round(precio_act - monto_act, 2)
                        df_servicios.at[i, 'estado_motorizado'] = r_edit['estado_motorizado']

                if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, f"Actualizadas comisiones/vueltas de {moto_sel}"):
                    st.success("✅ ¡Cambios guardados en GitHub con éxito!")
                    st.rerun()

            st.markdown("---")

            # Módulo de Teléfono y WhatsApp
            tel_moto = ""
            if not df_motos.empty and 'telefono' in df_motos.columns:
                m_info = df_motos[df_motos['nombre'].astype(str).str.strip().str.lower() == str(moto_sel).strip().lower()]
                if not m_info.empty:
                    tel_moto = str(m_info.iloc[0]['telefono']).replace("+", "").replace(" ", "").replace("-", "")

            vueltas_mo['fecha_dt'] = pd.to_datetime(vueltas_mo['fecha'], errors='coerce')
            vueltas_mo = vueltas_mo.sort_values(by='fecha_dt', ascending=True)

            msg_wa_m = f"🧾 *CORTE DE CUENTA - MOTOVUELTAS*\nMotorizado: *{moto_sel}*\n\n"
            for f_corta in vueltas_mo['fecha_corta'].unique():
                if f_corta:
                    msg_wa_m += f"📅 *{f_corta}*\n"
                    for _, r in vueltas_mo[vueltas_mo['fecha_corta'] == f_corta].iterrows():
                        msg_wa_m += f"▪ {r['origen']} ➡️ {r['destino']} = *${float(r['precio_cliente']):.2f}*\n"
                    msg_wa_m += "\n"
            
            if not df_avances_moto.empty:
                msg_wa_m += "💵 *ADELANTOS RECIBIDOS:*\n"
                for _, av_row in df_avances_moto.iterrows():
                    msg_wa_m += f"▪ {av_row['fecha_corta']}: -${float(av_row['monto']):.2f} ({av_row['concepto']})\n"
                msg_wa_m += "\n"
                
            msg_wa_m += "───────────────\n"
            msg_wa_m += f"💵 *Total Comisiones:* ${total_comision:.2f}\n"
            if total_avances > 0:
                msg_wa_m += f"📉 *Adelantos Restados:* -${total_avances:.2f}\n"
            msg_wa_m += f"💰 *TOTAL NETO A COBRAR: ${saldo_neto_pagar:.2f}*"

            col_wa_m, col_bot_m = st.columns([2, 1])
            with col_wa_m:
                st.markdown("📱 **Mensaje de Control para WhatsApp:**")
                st.code(msg_wa_m, language="text")
            with col_bot_m:
                st.write("")
                st.write("")
                if tel_moto:
                    st.link_button("📲 Abrir Chat WhatsApp", f"https://wa.me/{tel_moto}", use_container_width=True)
                else:
                    st.caption("⚠️ Motorizado sin teléfono registrado")

            st.markdown("---")

            # 7. BOTÓN PARA LIQUIDAR Y CAMBIAR ESTATUS
            confirmar_corte_m = st.checkbox(f"⚠️ Confirmar pago y cambio de status de estas {len(vueltas_mo)} vueltas a PAGADAS para {moto_sel}.", key="check_pago_moto")
            if st.button(f"✅ Liquidar y Marcar Vueltas como PAGADAS", type="primary", disabled=not confirmar_corte_m, use_container_width=True):
                ids_a_pagar = vueltas_mo['id'].tolist()
                df_servicios.loc[df_servicios['id'].isin(ids_a_pagar), 'estado_motorizado'] = 'Pagado'
    
                # Marcar también los adelantos del periodo como pagados en avances.csv
                if not df_avances_moto.empty:
                    ids_avances_pagar = df_avances_moto['id'].tolist()
                    if 'estado_avance' not in df_avances.columns:
                        df_avances['estado_avance'] = 'Pendiente'
                    df_avances.loc[df_avances['id'].isin(ids_avances_pagar), 'estado_avance'] = 'Pagado'
                    guardar_csv_en_github(FILE_AVANCES, df_avances, sha_avances, f"Adelantos liquidados de {moto_sel}")

                if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, f"Liquidacion realizada a motorizado {moto_sel}"):
                    st.success(f"✅ ¡Se han liquidado {len(ids_a_pagar)} vueltas de {moto_sel} correctamente!")
                    st.rerun()
        else:
            st.info("No se encontraron vueltas con el filtro seleccionado.")
    else:
        st.info("No hay motorizados o servicios registrados.")
