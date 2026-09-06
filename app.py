import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MotoVueltas v2", page_icon="🏍️", layout="wide")

# --- CREDENCIALES GITHUB ---
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "motovueltas-maker/Motovueltas-v2")
BRANCH = "main"

FILE_MOTORIZADOS = "motorizados.csv"
FILE_CLIENTES = "clientes.csv"
FILE_USUARIOS = "usuarios.csv"
FILE_SERVICIOS = "servicios.csv"

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
    opciones = ["Validar Vueltas", "Registrar Vuelta", "Corte Clientes", "Corte Motorizados", "Directorio Clientes", "Perfiles Motorizados"]
else:
    opciones = ["Registrar Vuelta"]

opcion_menu = st.sidebar.radio("Módulo:", opciones)

# --- CARGA GENERAL DE DATOS ---
df_motos, sha_motos = cargar_csv_desde_github(FILE_MOTORIZADOS)
df_clientes, sha_clientes = cargar_csv_desde_github(FILE_CLIENTES)
df_servicios, sha_servicios = cargar_csv_desde_github(FILE_SERVICIOS)

# --- MÓDULO: REGISTRAR VUELTA (COMPACTO) ---
if opcion_menu == " Registrar Vuelta":
    st.subheader("⚡ Registrar Nueva Vuelta / Carrera")
    
    # === PARAMETROS FIJOS (FUERA DEL RECUADRO REFRESCABLE) ===
    if st.session_state.rol == "Admin":
        col_f1, col_f2, col_f3 = st.columns([1, 1, 1])
        with col_f1:
            fecha_fija = st.date_input("📅 Fecha", value=datetime.today())
        with col_f2:
            nom_motos = df_motos['nombre'].tolist() if not df_motos.empty else []
            mot_sel_fijo = st.selectbox("🏍️ Motorizado", nom_motos)
        with col_f3:
            # Obtener porcentaje por defecto del motorizado seleccionado
            com_def = 66.67
            if not df_motos.empty and mot_sel_fijo in df_motos['nombre'].values:
                com_def = float(df_motos[df_motos['nombre'] == mot_sel_fijo]['porcentaje_ganancia'].values[0])
            comision_fija = st.number_input("% Ganancia Moto", min_value=0.0, max_value=100.0, value=com_def, step=0.5)
    else:
        # Para Motorizado no Admin solo la fecha queda fuera
        col_f1, _ = st.columns([1, 2])
        with col_f1:
            fecha_fija = st.date_input("📅 Fecha", value=datetime.today())
        mot_sel_fijo = st.session_state.usuario.capitalize()
        comision_fija = 66.67
        
        # Buscar comisión base si existe en base de datos
        if not df_motos.empty and mot_sel_fijo in df_motos['nombre'].values:
            comision_fija = float(df_motos[df_motos['nombre'] == mot_sel_fijo]['porcentaje_ganancia'].values[0])

    fecha_str = fecha_fija.strftime("%Y-%m-%d")

    # === FORMULARIO QUE SE REFRESCA AL REGISTRAR ===
    with st.form("form_nueva_vuelta_compacta", clear_on_submit=True):
        nom_clientes = df_clientes['nombre'].tolist() if not df_clientes.empty else []
        
        # Selección de cliente siempre vacía por defecto
        cli_sel = st.selectbox(
            "Cliente *", 
            nom_clientes, 
            index=None, 
            placeholder="Selecciona un cliente..."
        )

        # Campos en columnas compactas con texto fantasma (placeholder)
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

                # Lógica de Validación automática para Admin
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

# --- MÓDULO: DIRECTORIO Y EDICIÓN DE CLIENTES ---
elif opcion_menu == " Directorio Clientes":
    st.header("👥 Gestión y Directorio de Clientes")
    
    col_c1, col_c2 = st.columns([1, 1])
    
    # 1. FORMULARIO ULTRACOMPACTO: AGREGAR CLIENTE
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
                    nueva_c = pd.DataFrame([{
                        "id": tel_c, 
                        "nombre": nom_c, 
                        "telefono": tel_c, 
                        "ubicacion": ubi_c if ubi_c else "Local", 
                        "saldo_pendiente": 0.0
                    }])
                    df_clientes = pd.concat([df_clientes, nueva_c], ignore_index=True)
                    if guardar_csv_en_github(FILE_CLIENTES, df_clientes, sha_clientes, f"Nuevo cliente {nom_c}"):
                        st.success(f"✅ Cliente '{nom_c}' agregado exitosamente.")
                        st.rerun()

    # 2. FORMULARIO: EDITAR CLIENTE EXISTENTE (BUSCADOR VACÍO POR DEFECTO)
    with col_c2:
        st.subheader("✏️ Editar Cliente Existente")
        nom_clientes_lista = df_clientes['nombre'].tolist() if not df_clientes.empty else []
        
        # Campo de búsqueda completamente vacío por defecto
        cliente_a_editar = st.selectbox(
            "Seleccionar Cliente a Modificar", 
            nom_clientes_lista, 
            index=None, 
            placeholder="Buscar o seleccionar cliente..."
        )
        
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
    
    # 3. TABLA VISUAL DE CLIENTES (SIN MOSTRAR ID SEPARADO)
    st.subheader("📋 Lista de Clientes Registrados")
    if not df_clientes.empty:
        # Se muestra una vista limpia con Nombre, Teléfono y Ubicación
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

            # Filtrar servicios del cliente seleccionado
            df_cli_all = df_servicios[df_servicios['cliente'].astype(str).str.strip().str.lower() == str(cliente_sel).strip().lower()].copy()

            # 1. FILTRO POR FECHAS (DESDE - HASTA OPCIONAL)
            st.markdown("##### 📅 Filtrar Reporte por Fechas")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                f_desde_c = st.date_input("Fecha Desde (Opcional):", value=None, format="DD/MM/YYYY", key="f_desde_corte")
            with col_f2:
                f_hasta_c = st.date_input("Fecha Hasta (Opcional):", value=None, format="DD/MM/YYYY", key="f_hasta_corte")

            # Aplicar filtro de fecha
            fechas_cli_str = pd.to_datetime(df_cli_all['fecha'], errors='coerce').dt.strftime('%Y-%m-%d')

            if f_desde_c and f_hasta_c:
                f_ini_s = f_desde_c.strftime('%Y-%m-%d')
                f_fin_s = f_hasta_c.strftime('%Y-%m-%d')
                pendientes = df_cli_all[(fechas_cli_str >= f_ini_s) & (fechas_cli_str <= f_fin_s)].copy()
            elif f_desde_c:
                f_ini_s = f_desde_c.strftime('%Y-%m-%d')
                pendientes = df_cli_all[fechas_cli_str == f_ini_s].copy()
            elif f_hasta_c:
                f_fin_s = f_hasta_c.strftime('%Y-%m-%d')
                pendientes = df_cli_all[fechas_cli_str == f_fin_s].copy()
            else:
                # SI NO HAY FECHAS, MUESTRA TODAS LAS VUELTAS PENDIENTES
                pendientes = df_cli_all[df_cli_all['estado_cliente'] == 'Pendiente'].copy()

            # Función para formatear fecha a DD/MM
            def formatear_dd_mm(val):
                if pd.isna(val) or not str(val).strip() or str(val).lower() == 'none':
                    return ""
                try:
                    dt = pd.to_datetime(val, errors='coerce')
                    if pd.notnull(dt):
                        return dt.strftime('%d/%m')
                    val_str = str(val)[:10]
                    parts = val_str.split('-')
                    if len(parts) == 3:
                        return f"{parts[2]}/{parts[1]}"
                    return val_str[:5]
                except:
                    return str(val)[:5]

            pendientes['fecha_corta'] = pendientes['fecha'].apply(formatear_dd_mm)
            total_deuda = pendientes['precio_cliente'].astype(float).sum()

            # Métricas Rápidas
            c_m1, c_m2 = st.columns(2)
            c_m1.metric("Pendiente por Cobrar ($)", f"${total_deuda:.2f}")
            c_m2.metric("Vueltas Filtradas / Pendientes", len(pendientes))

            st.markdown("---")

            # 2. SECCIÓN DE ABONOS Y CHAT DIRECTO WHATSAPP
            col_abono, col_wa = st.columns([2, 1])

            with col_abono:
                abono_cliente = st.number_input("💵 Registrar Abono / Descuento ($):", min_value=0.0, max_value=float(total_deuda) if total_deuda > 0 else 0.0, value=0.0, step=0.5)

            # Obtener teléfono del cliente
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

                # 3. GENERACIÓN DEL MENSAJE PARA WHATSAPP
                total_neto = max(0.0, total_deuda - abono_cliente)

                msg_whatsapp = f"🧾 *REPORTE DE CUENTA - MOTOVUELTAS*\n"
                msg_whatsapp += f"Cliente: *{cliente_sel}*\n\n"

                fechas_unicas = pendientes['fecha_corta'].unique()

                for f_corta in fechas_unicas:
                    if f_corta:
                        msg_whatsapp += f"📅 *{f_corta}*\n"
                        vueltas_dia = pendientes[pendientes['fecha_corta'] == f_corta]
                        for _, r in vueltas_dia.iterrows():
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

                # 4. BOTÓN DE LIQUIDAR
                st.markdown("##### ⚙️ Liquidación de Servicios")
                confirmar_pago = st.checkbox(f"⚠️ Confirmar que deseas marcar estas {len(pendientes)} vueltas como PAGADAS.", key="check_pago_seguro")

                if st.button(f"✅ Marcar todas estas vueltas de {cliente_sel} como PAGADAS", type="primary", disabled=not confirmar_pago, use_container_width=True):
                    ids_a_pagar = pendientes['id'].tolist()
                    df_servicios.loc[df_servicios['id'].isin(ids_a_pagar), 'estado_cliente'] = 'Pagado'

                    if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, f"Liquidacion de vueltas para {cliente_sel}"):
                        st.success(f"✅ ¡Se han marcado {len(ids_a_pagar)} vueltas de {cliente_sel} como PAGADAS correctamente!")
                        st.rerun()
            else:
                st.info(f"No hay servicios pendientes o dentro del rango seleccionado para {cliente_sel}.")
    else:
        st.info("No hay servicios registrados en la base de datos.")

    # --- TAB 2: BUSCADOR Y EDICIÓN DIRECTA EN TABLA ---
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
            fechas_str = pd.to_datetime(df_filtrado['fecha'], errors='coerce').dt.strftime('%Y-%m-%d')
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

            df_filtrado['fecha_corta'] = df_filtrado['fecha'].apply(formatear_dd_mm)
            df_filtrado['eliminar'] = False

            st.markdown(f"**Vueltas encontradas:** {len(df_filtrado)}")
            if not df_filtrado.empty:
                column_config = {
                    "eliminar": st.column_config.CheckboxColumn("🗑️ Borrar", default=False),
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "fecha_corta": st.column_config.TextColumn("Fecha (DD/MM)"),
                    "cliente": st.column_config.SelectboxColumn("Cliente", options=nom_cli_l, required=True),
                    "motorizado": st.column_config.SelectboxColumn("Motorizado", options=nom_motos_l, required=True),
                    "origen": st.column_config.TextColumn("Desde"),
                    "destino": st.column_config.TextColumn("Hasta"),
                    "precio_cliente": st.column_config.NumberColumn("Precio ($)", format="$%.2f", min_value=0.0, step=0.5),
                    "estado_cliente": st.column_config.SelectboxColumn("Estado Pago", options=["Pendiente", "Pagado"])
                }
                column_order = ["eliminar", "id", "fecha_corta", "cliente", "motorizado", "origen", "destino", "precio_cliente", "estado_cliente"]

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

                    if guardar_csv_en_github(FILE_SERVICIOS, df_servicios, sha_servicios, "Edicion directa desde la tabla de vueltas"):
                        st.success("✅ ¡Cambios guardados correctamente!")
                        st.rerun()
        else:
            st.info("No hay servicios registrados.")
