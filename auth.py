import streamlit as st
import os

def inicializar_autenticacao():
    senha_correta = os.environ.get("SENHA_ZEUS", "cx_admin")
    
    # Lê o que está na URL atual
    senha_url = st.query_params.get("auth", "")
    convidado_url = st.query_params.get("guest", "")

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
                        
                        # O TRUQUE MÁGICO: Atualiza a URL no navegador do usuário automaticamente!
                        st.query_params["auth"] = senha_correta
                        
                        st.rerun()
                    else:
                        st.error("Chave inválida. Tente novamente.")
                
                st.divider()
                st.markdown("### Visitante / Portfólio")
                st.write("Quer ver como a IA funciona na prática? Você tem direito a 2 análises de teste.")
                if st.button("Entrar no Modo Convidado", use_container_width=True):
                    st.session_state.guest_mode = True
                    
                    # Salva na URL que ele é um convidado para não bugar no F5
                    st.query_params["guest"] = "true"
                    
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