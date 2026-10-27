import io
import os
import re
import tempfile
import time

from pydub import AudioSegment
from pydub.effects import normalize

MODELO_WHISPER = "whisper-large-v3"
CHUNK_ALVO_MS = 4 * 60 * 1000   # ~4 min por pedaço (16 kHz mono 16 bits = ~7,7 MB)
JANELA_BUSCA_MS = 10_000        # procura um ponto de baixo volume antes do corte
PASSO_MS = 250
PAD_FALA_MS = 400               # folga ao redor de cada trecho de voz
GAP_ENTRE_FALAS_MS = 300        # silêncio curto colocado entre trechos de voz

# Somente vocabulário (frases de instrução são repetidas pelo Whisper como se fossem fala)
PROMPT_WHISPER = "CS2, gaming, toxicidade, palavrões, ofensa, gameplay, report, ban."

# Frases que o Whisper costuma "inventar" em ruído/silêncio
ALUCINACOES = re.compile(
    r"(transcri\w*\s+literal|sem\s+censura|gracias\s+por\s+ver|obrigad[oa]\s+por\s+(assistir|ver)|"
    r"legendas?\s+pel[oa]|inscreva-se|subscribe|thanks\s+for\s+watching|amara\.org)",
    re.IGNORECASE,
)

# Repetições destes termos NUNCA são removidas (a contagem importa para a punição)
TERMOS_PRESERVAR = re.compile(
    r"(macac|mangac|mono|negr|pret[oa]|viad|veado|puta|fdp|vtnc|arromb|retard|estupr|estrup|"
    r"favelad|chimpanz|gorila|nazi|hitler|merda|caralho|porra|mata|matar)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Detecção de voz (VAD simples, relativo ao ruído de fundo de cada arquivo)
# ---------------------------------------------------------------------------
def _db_janelas(audio, janela_ms=100):
    valores = []
    for i in range(0, len(audio), janela_ms):
        db = audio[i:i + janela_ms].dBFS
        valores.append(-90.0 if db == float("-inf") else db)
    return valores


def _somente_voz(audio):
    """Mantém apenas os trechos com voz. Se nada for detectado, devolve o áudio original."""
    from pydub.silence import detect_nonsilent

    dbs = sorted(_db_janelas(audio))
    if not dbs:
        return audio
    piso = dbs[int(len(dbs) * 0.10)]                     # ruído de fundo (percentil 10)
    limiar = min(piso + 12, audio.dBFS - 6)

    trechos = detect_nonsilent(audio, min_silence_len=600, silence_thresh=limiar, seek_step=50)
    if not trechos:
        return audio

    resultado = AudioSegment.empty()
    gap = AudioSegment.silent(duration=GAP_ENTRE_FALAS_MS, frame_rate=audio.frame_rate)
    for ini, fim in trechos:
        ini = max(ini - PAD_FALA_MS, 0)
        fim = min(fim + PAD_FALA_MS, len(audio))
        resultado += audio[ini:fim] + gap
    return resultado if len(resultado) > 1000 else audio


# ---------------------------------------------------------------------------
# Divisão em pedaços (cortando em pontos de baixo volume)
# ---------------------------------------------------------------------------
def _achar_corte(audio, alvo_ms):
    inicio = max(alvo_ms - JANELA_BUSCA_MS, 0)
    melhor_t, melhor_db = alvo_ms, float("inf")
    for t in range(inicio, alvo_ms, PASSO_MS):
        db = audio[t:t + 300].dBFS
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


# ---------------------------------------------------------------------------
# Transcrição
# ---------------------------------------------------------------------------
def _g(obj, chave, padrao=None):
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
            texto = (_g(resp, "text", "") or "").strip()
            frases = re.split(r"(?<=[.!?…])\s+", texto)
            return [f.strip() for f in frases if f.strip() and not ALUCINACOES.search(f)]
        except Exception as e:
            ultimo_erro = e
            time.sleep(3 * (tentativa + 1))
    raise RuntimeError(f"Falha na transcrição após 3 tentativas: {ultimo_erro}")


def _colapsar_loops(linhas):
    """Remove loops de alucinação (mesma frase 4+ vezes seguidas), exceto termos ofensivos."""
    saida, anterior, repeticoes = [], None, 0
    for l in linhas:
        chave = re.sub(r"\W+", " ", l.lower()).strip()
        if chave == anterior:
            repeticoes += 1
        else:
            anterior, repeticoes = chave, 1
        if repeticoes > 3 and not TERMOS_PRESERVAR.search(chave):
            continue
        saida.append(l)
    return saida


def transcrever_audio(groq_client, arquivo_audio):
    """Recebe o arquivo do st.file_uploader e devolve a transcrição (um segmento por linha)."""
    sufixo = os.path.splitext(arquivo_audio.name)[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=sufixo) as tmp:
        tmp.write(arquivo_audio.getvalue())
        caminho = tmp.name

    try:
        audio = AudioSegment.from_file(caminho)
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)  # 16 kHz, mono, 16 bits
        if audio.dBFS == float("-inf"):
            return ""
        audio = normalize(audio, headroom=1.0)   # sobe o volume de áudios baixos
        audio = _somente_voz(audio)              # descarta ruído de fundo (onde o Whisper alucina)

        linhas = []
        for pedaco in _dividir(audio):
            linhas.extend(_transcrever_pedaco(groq_client, pedaco))
        return "\n".join(_colapsar_loops(linhas))
    finally:
        if os.path.exists(caminho):
            os.remove(caminho)