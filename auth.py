import streamlit as st
import os

def inicializar_autenticacao():
    senha_correta = os.environ.get("SENHA_ZEUS", "cx_admin")
    senha_url = st.query_params.get("auth", "")

    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = (senha_url == senha_correta)
    if 'guest_mode' not in st.session_state:
        st.session_state.guest_mode = False
    if 'guest_uses' not in st.session_state:
        st.session_state.guest_uses = 0

def verificar_acesso():
    senha_correta = os.environ.get("SENHA_ZEUS", "cx_admin")
    
    # Se não for admin e não clicou em modo convidado, trava na porta
    if not st.session_state.is_admin and not st.session_state.guest_mode:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.container(border=True):
                if os.path.exists("logo.png"):
                    st.image("logo.png", width=100)
                st.title("⚡ Zeus AI")
                st.markdown("Auditoria disciplinar e forense para eSports.")
                
                st.divider()
                
                st.markdown("### Acesso Restrito (Equipe GC)")
                senha_input = st.text_input("Insira a chave de acesso corporativa:", type="password")
                if st.button("Entrar no Zeus", type="primary", use_container_width=True):
                    if senha_input == senha_correta:
                        st.session_state.is_admin = True
                        st.rerun()
                    else:
                        st.error("Chave inválida. Tente novamente.")
                
                st.divider()
                st.markdown("### Visitante / Portfólio")
                st.write("Quer ver como a IA funciona na prática? Você tem direito a 2 análises de teste.")
                if st.button("Entrar no Modo Convidado", use_container_width=True):
                    st.session_state.guest_mode = True
                    st.rerun()
        st.stop() # Interrompe a renderização do app aqui

def bloqueio_limite_convidado():
    if not st.session_state.is_admin and st.session_state.guest_uses >= 2:
        st.error("🔒 Limite de testes atingido! Insira a chave corporativa para continuar usando.")
        return True
    return False

def registrar_uso_convidado():
    if not st.session_state.is_admin:
        st.session_state.guest_uses += 1