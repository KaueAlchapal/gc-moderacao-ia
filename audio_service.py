import io
import os
import re
import tempfile
import time

from pydub import AudioSegment
from pydub.effects import normalize

MODELO_WHISPER = "whisper-large-v3"
CHUNK_ALVO_MS = 5 * 60 * 1000   # ~5 min por pedaço (mono 16 kHz = ~9,6 MB)
JANELA_BUSCA_MS = 10_000        # procura silêncio nos 10 s antes do corte
PASSO_MS = 250
LIMITE_SILENCIO_DBFS = -55      # pedaço mais baixo que isso é tratado como silêncio

# Só vocabulário (sem frases de instrução, o Whisper as repete como se fossem fala)
PROMPT_WHISPER = "CS2, gaming, toxicidade, palavrões, ofensa, gameplay, report, ban."

# Frases que o Whisper costuma "inventar" em silêncio/ruído
ALUCINACOES = re.compile(
    r"(transcri\w*\s+literal|sem\s+censura|gracias\s+por\s+ver|obrigad[oa]\s+por\s+(assistir|ver)|"
    r"legendas?\s+pel[oa]|inscreva-se|subscribe|thanks\s+for\s+watching|"
    r"amara\.org|tchau\.?$)",
    re.IGNORECASE,
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


def _g(obj, chave, padrao=None):
    """Lê um campo tanto de dict quanto de objeto."""
    if isinstance(obj, dict):
        return obj.get(chave, padrao)
    return getattr(obj, chave, padrao)


def _obter_segmentos(resp):
    segs = _g(resp, "segments")
    if segs is None:
        extra = getattr(resp, "model_extra", None) or {}
        segs = extra.get("segments")
    return segs


def _segmento_valido(seg):
    """Descarta segmentos que parecem alucinação do Whisper."""
    texto = (_g(seg, "text", "") or "").strip()
    if not texto or ALUCINACOES.search(texto):
        return False
    no_speech = _g(seg, "no_speech_prob", 0.0) or 0.0
    logprob = _g(seg, "avg_logprob", 0.0) or 0.0
    compressao = _g(seg, "compression_ratio", 0.0) or 0.0
    if no_speech > 0.6 and logprob < -1.0:
        return False
    if compressao > 2.4 and logprob < -0.8:
        return False
    return True


def _transcrever_pedaco(groq_client, pedaco):
    buffer = io.BytesIO()
    pedaco.export(buffer, format="wav")
    dados = buffer.getvalue()

    ultimo_erro = None
    for tentativa in range(3):
        try:
            resp = groq_client.audio.transcriptions.create(
                file=("audio.wav", dados),
                model=MODELO_WHISPER,
                prompt=PROMPT_WHISPER,
                response_format="verbose_json",
                temperature=0.0,
            )
            segs = _obter_segmentos(resp)
            if segs:
                linhas = [(_g(s, "text", "") or "").strip() for s in segs if _segmento_valido(s)]
                return [l for l in linhas if l]
            # Fallback: sem segmentos, usa o texto bruto filtrado por frase
            texto = (_g(resp, "text", "") or "").strip()
            frases = re.split(r"(?<=[.!?…])\s+", texto)
            return [f.strip() for f in frases if f.strip() and not ALUCINACOES.search(f)]
        except Exception as e:
            ultimo_erro = e
            time.sleep(3 * (tentativa + 1))
    raise RuntimeError(f"Falha na transcrição após 3 tentativas: {ultimo_erro}")


def transcrever_audio(groq_client, arquivo_audio):
    """Recebe o arquivo do st.file_uploader e devolve a transcrição (uma frase/segmento por linha)."""
    sufixo = os.path.splitext(arquivo_audio.name)[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=sufixo) as tmp:
        tmp.write(arquivo_audio.getvalue())
        caminho = tmp.name

    try:
        audio = AudioSegment.from_file(caminho)
        audio = audio.set_frame_rate(16000).set_channels(1)
        if audio.dBFS != float("-inf"):
            audio = normalize(audio, headroom=1.0)  # sobe o volume de áudios baixos

        linhas = []
        for pedaco in _dividir(audio):
            if pedaco.dBFS < LIMITE_SILENCIO_DBFS:  # pedaço praticamente mudo: nem envia
                continue
            linhas.extend(_transcrever_pedaco(groq_client, pedaco))
        return "\n".join(linhas)
    finally:
        if os.path.exists(caminho):
            os.remove(caminho)