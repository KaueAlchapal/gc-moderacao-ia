import io
import os
import tempfile
import time

from pydub import AudioSegment

MODELO_WHISPER = "whisper-large-v3"
CHUNK_ALVO_MS = 5 * 60 * 1000   # ~5 min por pedaço (mono 16 kHz = ~9,6 MB, abaixo do limite)
JANELA_BUSCA_MS = 10_000        # procura um momento de silêncio nos 10 s antes do corte
PASSO_MS = 250

PROMPT_BASE = (
    "Conversa de jogadores em uma partida de CS2, em português do Brasil e às vezes em espanhol, "
    "com gírias e palavrões. Transcrição literal, sem censura."
)


def _achar_corte(audio, alvo_ms):
    """Escolhe o ponto de menor volume perto do alvo para não cortar palavras ao meio."""
    inicio = max(alvo_ms - JANELA_BUSCA_MS, 0)
    melhor_t, melhor_db = alvo_ms, float("inf")
    for t in range(inicio, alvo_ms, PASSO_MS):
        db = audio[t:t + 300].dBFS  # -inf para silêncio total
        if db < melhor_db:
            melhor_db, melhor_t = db, t
    return melhor_t


def _dividir(audio):
    pedacos, pos, total = [], 0, len(audio)
    while pos < total:
        if total - pos <= CHUNK_ALVO_MS + JANELA_BUSCA_MS:
            pedacos.append(audio[pos:])
            break
        corte = _achar_corte(audio, pos + CHUNK_ALVO_MS)
        pedacos.append(audio[pos:corte])
        pos = corte
    return pedacos


def _transcrever_pedaco(groq_client, pedaco, prompt):
    buffer = io.BytesIO()
    pedaco.export(buffer, format="wav")
    dados = buffer.getvalue()

    ultimo_erro = None
    for tentativa in range(3):
        try:
            resp = groq_client.audio.transcriptions.create(
                file=("audio.wav", dados),
                model=MODELO_WHISPER,
                prompt=prompt,
                temperature=0.0,
            )
            return resp.text.strip()
        except Exception as e:
            ultimo_erro = e
            time.sleep(3 * (tentativa + 1))
    raise RuntimeError(f"Falha na transcrição após 3 tentativas: {ultimo_erro}")


def transcrever_audio(groq_client, arquivo_audio):
    """Recebe o arquivo do st.file_uploader e devolve a transcrição completa."""
    sufixo = os.path.splitext(arquivo_audio.name)[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=sufixo) as tmp:
        tmp.write(arquivo_audio.getvalue())
        caminho = tmp.name

    try:
        audio = AudioSegment.from_file(caminho)
        audio = audio.set_frame_rate(16000).set_channels(1)  # reduz tamanho sem perder fala
        pedacos = _dividir(audio)

        textos = []
        for pedaco in pedacos:
            # Continuidade: o fim do pedaço anterior ajuda o Whisper no começo do próximo
            contexto = textos[-1][-150:] if textos else ""
            prompt = f"{PROMPT_BASE} {contexto}".strip()
            textos.append(_transcrever_pedaco(groq_client, pedaco, prompt))
        return " ".join(t for t in textos if t)
    finally:
        if os.path.exists(caminho):
            os.remove(caminho)