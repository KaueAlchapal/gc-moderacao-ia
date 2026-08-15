import streamlit as st
import os

def inicializar_autenticacao():
    senha_correta = os.environ.get("SENHA_ZEUS", "cx_admin")
    
    # BLINDAGEM DE VERSÃO
    try:
        senha_url = st.query_params.get("auth", "")
        convidado_url = st.query_params.get("guest", "")
    except AttributeError:
        # Fallback para versões mais antigas do Streamlit Cloud
        params = st.experimental_get_query_params()
        senha_url = params.get("auth", [""])[0]
        convidado_url = params.get("guest", [""])[0]

    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = (senha_url == senha_correta)
    
    if 'guest_mode' not in st.session_state:
        st.session_state.guest_mode = (convidado_url == "true")
        
    if 'guest_uses' not in st.session_state:
        st.session_state.guest_uses = 0

def verificar_acesso():
    senha_correta = os.environ.get("SENHA_ZEUS", "cx_admin")
    
    # Se não for admin e não clicou em modo convidado, mostra a porta
    if not st.session_state.is_admin and not st.session_state.guest_mode:
        
        # Coluna central ligeiramente mais larga para acomodar as duas opções
        col1, col2, col3 = st.columns([1, 2.5, 1])
        
        with col2:
            with st.container(border=True):

               # CABEÇALHO CENTRALIZADO
                col_logo1, col_logo2, col_logo3 = st.columns([2.5, 1, 2.5]) 
                with col_logo2:
                    if os.path.exists("logo.png"):
                        st.image("logo.png", use_container_width=True)
                
                st.markdown("<h2 style='text-align: center;' anchor=False>⚡ Zeus AI</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: #a0a0a0; margin-top: -10px;'>Auditoria disciplinar e forense para eSports.</p>", unsafe_allow_html=True)
                
                st.divider()
                
                # OPÇÕES LADO A LADO
                col_admin, col_guest = st.columns(2, gap="large")
                
                with col_admin:
                    st.markdown("### 🛡️ Equipe GC")
                    st.caption("Acesso ilimitado para operação diária.")
                    
                    senha_input = st.text_input("Chave corporativa:", type="password", placeholder="Insira a chave...", label_visibility="collapsed")
                    
                    if st.button("Entrar no Zeus", type="primary", use_container_width=True):
                        if senha_input == senha_correta:
                            st.session_state.is_admin = True
                            
                            # BLINDAGEM DE VERSÃO
                            try:
                                st.query_params["auth"] = senha_correta
                            except AttributeError:
                                st.experimental_set_query_params(auth=senha_correta)
                                
                            st.rerun()
                        else:
                            st.error("Chave inválida.")
                
                with col_guest:
                    st.markdown("### 👤 Visitante")
                    st.caption("Teste a IA na prática.")
                    
                    # Espaçamento invisível para alinhar os botões
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    if st.button("Acessar Modo Convidado", use_container_width=True):
                        st.session_state.guest_mode = True
                        
                        # BLINDAGEM DE VERSÃO (convidado)
                        try:
                            st.query_params["guest"] = "true"
                        except AttributeError:
                            st.experimental_set_query_params(guest="true")
                            
                        st.rerun()
        st.stop()

def bloqueio_limite_convidado():
    if not st.session_state.is_admin and st.session_state.guest_uses >= 2:
        st.error("🔒 Limite de testes atingido! Insira a chave corporativa para continuar usando.")
        return True
    return False

def registrar_uso_convidado():
    if not st.session_state.is_admin:
        st.session_state.guest_uses += 1