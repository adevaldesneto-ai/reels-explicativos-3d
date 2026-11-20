# -*- coding: utf-8 -*-
"""
Motor de videos explicativos (estilo reels 3D low-poly, legenda palavra a palavra).

Uso:
  python motor.py alinhar <projeto>   # gera palavras.json a partir de narracao.mp3 (faster-whisper)
  python motor.py render  <projeto>   # gera video.mp4
  python motor.py sfx     <projeto>   # so exporta os efeitos sonoros (teste)

<projeto> e uma pasta com: roteiro.json, narracao.mp3 (ou .wav) e img/*.jpg
Requisitos: Python 3.9+, ffmpeg no PATH, pip install pillow numpy faster-whisper.
Fonte recomendada: Montserrat ExtraBold em scripts/fontes/ (veja o README).
Licenca: MIT.
"""
import json, math, os, random, re, subprocess, sys, unicodedata, wave, difflib
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ----------------------------------------------------------------- estilo fixo
ESTILO = {
    "W": 1080, "H": 1920, "FPS": 30,
    "legenda_y": 0.73,          # palavra falada: parte de baixo do video
    "legenda_tam": 92,          # px
    "legenda_contorno": 9,
    "sticker_y": 0.20,          # exclamacao no topo
    "sticker_tam": 118,
    "rotulo_y": 0.84,           # rotulo embaixo da legenda
    "rotulo_tam": 64,
    "amarelo": (255, 196, 40), "vermelho": (238, 64, 58), "coral": (255, 92, 92), "azul": (70, 165, 255),
    "branco": (255, 255, 255), "preto": (20, 20, 20),
    "vol_voz": 1.0, "vol_sfx": 0.55, "vol_musica": 0.10,
}

FONTES = [
    "Montserrat-ExtraBold.ttf", "Montserrat-Black.ttf", "Poppins-ExtraBold.ttf", "Poppins-Bold.ttf",
    "C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/seguibl.ttf", "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Black.ttf", "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
_cache_fonte = {}


def fonte(tam):
    if tam in _cache_fonte:
        return _cache_fonte[tam]
    aqui = os.path.dirname(os.path.abspath(__file__))
    for f in FONTES:
        for cand in (os.path.join(aqui, "fontes", f), f):
            if os.path.exists(cand):
                _cache_fonte[tam] = ImageFont.truetype(cand, tam)
                return _cache_fonte[tam]
    _cache_fonte[tam] = ImageFont.load_default()
    return _cache_fonte[tam]


# ----------------------------------------------------------------- utilidades
def norm(p):
    p = unicodedata.normalize("NFD", p.lower())
    p = "".join(c for c in p if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", p)


def tokens(texto):
    return [t for t in re.split(r"\s+", texto.strip()) if t]


def ease_out_back(t):
    c1, c3 = 1.70158, 2.70158
    t = min(max(t, 0), 1)
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_in_out(t):
    t = min(max(t, 0), 1)
    return 0.5 - 0.5 * math.cos(math.pi * t)


def ler_audio(caminho, sr=44100):
    """Decodifica qualquer audio para float32 mono via ffmpeg."""
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", caminho, "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, np.float32).copy()


def achar_narracao(proj):
    for n in ("narracao.mp3", "narracao.wav", "narracao.m4a"):
        if os.path.exists(os.path.join(proj, n)):
            return os.path.join(proj, n)
    return None


# ----------------------------------------------------------------- efeitos sonoros (sintetizados)
SR = 44100


def _env(n, a=0.005, r=None):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4))
    if r:
        e *= np.exp(-t / r)
    return e


def _ruido(n, seed=0):
    return np.random.default_rng(seed).standard_normal(n)


def _lowpass(x, alpha):
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc += alpha * (v - acc); y[i] = acc
    return y


def sfx_whoosh(d=0.45):
    n = int(SR * d); t = np.linspace(0, 1, n)
    x = _ruido(n, 1)
    # filtro passa-baixa variavel (sweep) -> "fuuush"
    y = np.empty(n); acc = 0.0
    for i in range(n):
        a = 0.02 + 0.35 * math.sin(math.pi * t[i]) ** 2
        acc += a * (x[i] - acc); y[i] = acc
    return y * np.sin(np.pi * t) ** 1.5 * 1.6


def sfx_pop(d=0.12):
    n = int(SR * d); t = np.arange(n) / SR
    f = 900 * np.exp(-t * 25) + 300
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.001, 0.03) * 0.9


def sfx_impacto(d=0.5):
    n = int(SR * d); t = np.arange(n) / SR
    f = 120 * np.exp(-t * 8) + 45
    grave = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.002, 0.15)
    estouro = _lowpass(_ruido(n, 2), 0.25) * _env(n, 0.001, 0.04)
    return (grave * 1.0 + estouro * 0.8)


def sfx_ding(d=0.9):
    n = int(SR * d); t = np.arange(n) / SR
    y = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((1568, 1), (3136, .35), (4704, .15)))
    return y * _env(n, 0.002, 0.25) * 0.45


def sfx_boing(d=0.6):
    n = int(SR * d); t = np.arange(n) / SR
    f = 260 + 140 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 4) - 120 * t
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.003, 0.25) * 0.7


def sfx_estalo(d=0.35):
    """'crack' de algo rompendo."""
    n = int(SR * d)
    x = _ruido(n, 3) * _env(n, 0.0005, 0.02)
    x[int(SR * 0.05):] += _ruido(n - int(SR * 0.05), 4) * _env(n - int(SR * 0.05), 0.0005, 0.03) * 0.7
    return x * 0.9


def sfx_escorrega(d=0.5):
    n = int(SR * d); t = np.arange(n) / SR
    f = 700 - 900 * t
    return np.sin(2 * np.pi * np.cumsum(np.maximum(f, 120)) / SR) * _env(n, 0.01, 0.3) * 0.45


def sfx_tique(d=0.05):
    n = int(SR * d)
    return _lowpass(_ruido(n, 5), 0.5) * _env(n, 0.0005, 0.008) * 0.6


SFX = {"whoosh": sfx_whoosh, "pop": sfx_pop, "impacto": sfx_impacto, "ding": sfx_ding,
       "boing": sfx_boing, "estalo": sfx_estalo, "escorrega": sfx_escorrega, "tique": sfx_tique}


def sfx(nome, proj=None):
    """Usa um arquivo sfx/<nome>.wav/.mp3 do projeto ou da pasta do motor se existir; senao sintetiza."""
    aqui = os.path.dirname(os.path.abspath(__file__))
    for base in ([proj] if proj else []) + [aqui]:
        for ext in (".wav", ".mp3"):
            p = os.path.join(base, "sfx", nome + ext)
            if os.path.exists(p):
                return ler_audio(p)
    y = SFX[nome]()
    return (y / (np.abs(y).max() + 1e-9) * 0.9).astype(np.float32)


# ----------------------------------------------------------------- tempo das palavras
def alinhar(proj):
    try:  # usa os certificados do Windows (evita erro de SSL ao baixar o modelo na 1a vez)
        import truststore; truststore.inject_into_ssl()
    except Exception:
        pass
    from faster_whisper import WhisperModel
    narr = achar_narracao(proj)
    modelo = WhisperModel(os.environ.get("WHISPER_MODELO", "small"), device="cpu", compute_type="int8")
    segs, _ = modelo.transcribe(narr, language="pt", word_timestamps=True, vad_filter=False)
    pal = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)} for s in segs for w in s.words]
    json.dump(pal, open(os.path.join(proj, "palavras.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"{len(pal)} palavras alinhadas")


def tempos_do_roteiro(rot, proj, dur_total):
    """Devolve lista de (palavra_do_roteiro, inicio, fim, indice_cena) usando palavras.json se houver."""
    script = []
    for ci, c in enumerate(rot["cenas"]):
        for t in tokens(c["texto"]):
            script.append([t, None, None, ci])
    caminho = os.path.join(proj, "palavras.json")
    if os.path.exists(caminho):
        trans = json.load(open(caminho, encoding="utf-8"))
        a = [norm(s[0]) for s in script]; b = [norm(w["w"]) for w in trans]
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
                for k in range(i2 - i1):
                    script[i1 + k][1] = trans[j1 + k]["s"]; script[i1 + k][2] = trans[j1 + k]["e"]
            elif tag == "replace" and j2 > j1:
                s0, e0 = trans[j1]["s"], trans[j2 - 1]["e"]; n = i2 - i1
                for k in range(n):
                    script[i1 + k][1] = s0 + (e0 - s0) * k / n; script[i1 + k][2] = s0 + (e0 - s0) * (k + 1) / n
    # preencher buracos (sem alinhamento -> proporcional a letras)
    if all(s[1] is None for s in script):
        pesos = [len(s[0]) + 2 for s in script]; tot = sum(pesos); acc = 0.15
        usavel = dur_total - 0.3
        for s, p in zip(script, pesos):
            s[1] = acc; acc += usavel * p / tot; s[2] = acc
    else:
        for i, s in enumerate(script):
            if s[1] is None:
                prev = next((script[j][2] for j in range(i - 1, -1, -1) if script[j][2] is not None), 0.0)
                nxt = next((script[j][1] for j in range(i + 1, len(script)) if script[j][1] is not None), dur_total)
                run = 1
                while i + run < len(script) and script[i + run][1] is None:
                    run += 1
                passo = (nxt - prev) / (run + 0.0)
                for k in range(run):
                    script[i + k][1] = prev + passo * k; script[i + k][2] = prev + passo * (k + 1)
    return script


# ----------------------------------------------------------------- desenho de textos
def texto_contornado(txt, tam, cor, contorno, cor_contorno=(0, 0, 0), sombra=True, contorno2=0, cor2=(0, 0, 0)):
    f = fonte(tam)
    pad = contorno + contorno2 + 20
    bb = f.getbbox(txt, stroke_width=contorno + contorno2)
    w, h = bb[2] - bb[0] + pad * 2, bb[3] - bb[1] + pad * 2
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x, y = pad - bb[0], pad - bb[1]
    if sombra:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((x + 5, y + 7), txt, font=f, fill=(0, 0, 0, 150),
                                stroke_width=contorno + contorno2, stroke_fill=(0, 0, 0, 150))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(4)))
        d = ImageDraw.Draw(im)
    if contorno2:
        d.text((x, y), txt, font=f, fill=cor2, stroke_width=contorno + contorno2, stroke_fill=cor2)
    d.text((x, y), txt, font=f, fill=cor, stroke_width=contorno, stroke_fill=cor_contorno)
    return im


def caber(im, largura_max):
    """Encolhe o texto se ele passar da largura maxima (ex.: rotulos longos)."""
    if im.width <= largura_max:
        return im
    return im.resize((int(largura_max), max(1, int(im.height * largura_max / im.width))), Image.LANCZOS)


def colar_central(base, im, cx, cy, escala=1.0, angulo=0.0, alpha=1.0):
    if escala <= 0.01 or alpha <= 0.01:
        return
    if angulo:
        im = im.rotate(angulo, resample=Image.BICUBIC, expand=True)
    if abs(escala - 1) > 0.005:
        im = im.resize((max(1, int(im.width * escala)), max(1, int(im.height * escala))), Image.BILINEAR)
    if alpha < 1:
        a = im.getchannel("A").point(lambda v: int(v * alpha)); im.putalpha(a)
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


# ----------------------------------------------------------------- imagem de fundo animada
_cache_img = {}


def carregar_img(caminho, W, H, margem=1.22):
    if caminho in _cache_img:
        return _cache_img[caminho]
    if caminho and os.path.exists(caminho):
        im = Image.open(caminho).convert("RGB")
    else:
        im = Image.new("RGB", (W, H), (240, 210, 150))
        ImageDraw.Draw(im).text((40, H // 2), os.path.basename(str(caminho)), fill=(0, 0, 0), font=fonte(50))
    # cobre o quadro com folga para zoom/pan
    s = max(W * margem / im.width, H * margem / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    _cache_img[caminho] = im
    return im


def quadro_fundo(cena, t_local, dur, W, H, rnd):
    im = carregar_img(cena["_img"], W, H)
    mov = cena.get("movimento", "zoom_in")
    p = ease_in_out(t_local / max(dur, 0.01))
    z0, z1, dx0, dx1, dy0, dy1 = 1.0, 1.0, 0, 0, 0, 0
    if mov == "zoom_in":
        z0, z1 = 1.0, 1.15
    elif mov == "zoom_out":
        z0, z1 = 1.15, 1.0
    elif mov == "pan_esq":
        z0 = z1 = 1.08; dx0, dx1 = 0.06, -0.06
    elif mov == "pan_dir":
        z0 = z1 = 1.08; dx0, dx1 = -0.06, 0.06
    elif mov == "sobe":
        z0 = z1 = 1.08; dy0, dy1 = 0.06, -0.06
    elif mov == "desce":
        z0 = z1 = 1.08; dy0, dy1 = -0.06, 0.06
    elif mov == "parado":
        z0 = z1 = 1.03
    z = z0 + (z1 - z0) * p
    # batimento cardiaco (efeito "pulsar")
    for ef in cena.get("efeitos", []):
        if ef.get("tipo") == "pulsar":
            z *= 1 + ef.get("forca", 0.035) * batida(t_local, ef.get("bpm", 80))
    # "punch" de entrada: corte seco com leve zoom que assenta em 0,2 s
    if t_local < 0.2:
        z *= 1 + 0.07 * (1 - ease_in_out(t_local / 0.2))
    # foco opcional (zoom num ponto: cena["foco"]=[x,y] relativos)
    fx, fy = cena.get("foco", [0.5, 0.5])
    cw, ch = W / z, H / z  # imagem ja esta em escala 1:1 com o quadro (com folga de 22%)
    cx = im.width * (fx + (dx0 + (dx1 - dx0) * p)); cy = im.height * (fy + (dy0 + (dy1 - dy0) * p))
    # tremor (impacto)
    tr = cena.get("_tremor", [])
    for t0 in tr:
        dtt = t_local - t0
        if 0 <= dtt < 0.45:
            amp = 28 * math.exp(-dtt * 9)
            cx += rnd.uniform(-amp, amp); cy += rnd.uniform(-amp, amp)
    x0 = min(max(cx - cw / 2, 0), im.width - cw); y0 = min(max(cy - ch / 2, 0), im.height - ch)
    return im.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)).convert("RGBA")


# ----------------------------------------------------------------- animacoes desenhadas em Python
def batida(t, bpm=80):
    """Curva de batimento (tum-tum) entre 0 e ~1."""
    ph = (t % (60.0 / bpm)) / (60.0 / bpm)
    return math.exp(-((ph - 0.03) / 0.045) ** 2) + 0.6 * math.exp(-((ph - 0.22) / 0.045) ** 2)


_cache_grad = {}


def gradiente_radial(r, cor, alpha_max):
    chave = (r, cor, alpha_max)
    if chave not in _cache_grad:
        n = 256
        y, x = np.mgrid[0:n, 0:n]
        d = np.sqrt((x - n / 2) ** 2 + (y - n / 2) ** 2) / (n / 2)
        a = np.clip(1 - d, 0, 1) ** 0.8 * alpha_max
        arr = np.zeros((n, n, 4), np.uint8); arr[..., 0], arr[..., 1], arr[..., 2] = cor; arr[..., 3] = a.astype(np.uint8)
        _cache_grad[chave] = Image.fromarray(arr, "RGBA")
    return _cache_grad[chave].resize((max(2, int(2 * r)), max(2, int(2 * r))), Image.BILINEAR)


def _caminho_rachadura(seed, W):
    rnd = random.Random(seed); ramos = []
    for k in range(3):
        ang = -math.pi / 2 + (k - 1) * 1.0 + rnd.uniform(-0.3, 0.3)
        pts = [(0.0, 0.0)]; x = y = 0.0
        for _ in range(7):
            ang += rnd.uniform(-0.6, 0.6); passo = W * rnd.uniform(0.018, 0.03)
            x += math.cos(ang) * passo; y += math.sin(ang) * passo; pts.append((x, y))
        ramos.append(pts)
    return ramos


def aplicar_efeitos(frame, c, t, tl, W, H):
    """Efeitos animados por codigo, por cena (lista c['efeitos']). Coordenadas x, y, r relativas ao quadro."""
    efs = c.get("efeitos", [])
    if not efs:
        return frame
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for i, ef in enumerate(efs):
        tipo = ef.get("tipo"); t0 = ef.get("_t0", 0.0); dt = tl - t0
        if tipo == "fluxo":
            # celulas do sangue correndo de (x0,y0) para (x1,y1); param "parar_na_palavra" congela o fluxo
            x0, y0, x1, y1 = ef["x0"] * W, ef["y0"] * H, ef["x1"] * W, ef["y1"] * H
            L = math.hypot(x1 - x0, y1 - y0) or 1; ux, uy = (x1 - x0) / L, (y1 - y0) / L; px, py = -uy, ux
            vel = ef.get("vel", 0.55); ts = ef.get("_tstop")
            T = tl if ts is None or tl < ts else ts + 0.35 * (1 - math.exp(-(tl - ts) / 0.35))
            rnd = random.Random(11 + i); larg = ef.get("largura", 0.10) * W; tam = ef.get("tamanho", 0.04) * W
            for k in range(ef.get("n", 16)):
                s = (rnd.random() + vel * T) % 1.0; off = rnd.uniform(-1, 1) * larg / 2
                if ts is not None and tl > ts:
                    s = min(s, ef.get("limite", 0.55) - 0.04 * (k % 4))
                cx, cy = x0 + ux * L * s + px * off, y0 + uy * L * s + py * off
                w, h = tam, tam * 0.62
                d.ellipse([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], fill=(200, 38, 48, 235), outline=(120, 15, 25, 255), width=3)
                d.ellipse([cx - w / 5, cy - h / 6, cx + w / 5, cy + h / 6], fill=(150, 20, 30, 200))
        elif tipo == "rachadura" and dt >= 0:
            cx, cy = ef["x"] * W, ef["y"] * H; p = min(1, dt / 0.25)
            for ramo in _caminho_rachadura(5 + i, W):
                n = max(2, int(len(ramo) * p))
                pts = [(cx + a, cy + b) for a, b in ramo[:n]]
                d.line(pts, fill=(255, 245, 220, 255), width=11, joint="curve")
                d.line(pts, fill=(55, 25, 10, 255), width=6, joint="curve")
        elif tipo == "particulas" and 0 <= dt < 1.0:
            cx, cy = ef["x"] * W, ef["y"] * H; rnd = random.Random(21 + i); cor = tuple(ef.get("cor", (250, 205, 60)))
            for k in range(ef.get("n", 18)):
                ang = rnd.uniform(0, 2 * math.pi); v = rnd.uniform(0.25, 0.6) * W
                x = cx + math.cos(ang) * v * dt; y = cy + math.sin(ang) * v * dt + 0.9 * W * dt * dt
                s = W * 0.012 * (1 - dt); a = int(255 * (1 - dt))
                d.polygon([(x, y - s), (x + s, y + s), (x - s, y + s)], fill=cor + (a,))
        elif tipo == "escurecer" and dt >= 0:
            p = ease_in_out(dt / ef.get("dur", 1.4)); r = ef.get("r", 0.15) * W * (0.3 + 0.7 * p)
            g = gradiente_radial(int(r), tuple(ef.get("cor", (60, 25, 70))), int(ef.get("alpha", 200) * p))
            ov.alpha_composite(g, (int(ef["x"] * W - r), int(ef["y"] * H - r)))
        elif tipo == "alarme":
            a = int(ef.get("alpha", 70) * (0.5 + 0.5 * math.sin(2 * math.pi * 2.2 * tl)))
            d.rectangle([0, 0, W, H], fill=(230, 30, 30, a))
        elif tipo == "seta" and dt >= 0:  # seta branca com contorno, balancando; direcao: baixo|cima|esq|dir
            cx, cy = ef["x"] * W, ef["y"] * H; L = ef.get("tamanho", 0.16) * W; g = L * 0.35
            ang = {"baixo": 90, "cima": -90, "esq": 180, "dir": 0}.get(ef.get("direcao", "baixo"), 90)
            a = math.radians(ang); b = 0.025 * W * math.sin(dt * 9) * min(1, dt / 0.15)
            ux, uy = math.cos(a), math.sin(a); px, py = -uy, ux
            cx += ux * b; cy += uy * b
            pts = [(-L / 2, -g * 0.35), (L * 0.1, -g * 0.35), (L * 0.1, -g), (L / 2, 0), (L * 0.1, g), (L * 0.1, g * 0.35), (-L / 2, g * 0.35)]
            poly = [(cx + x * ux + y * px, cy + x * uy + y * py) for x, y in pts]
            d.polygon(poly, fill=(255, 255, 255, 245), outline=(20, 20, 20, 255), width=6)
        elif tipo == "brilho" and dt >= 0:  # anel que se expande (ex.: o coracao "pede socorro")
            p = (dt % 0.9) / 0.9; r = (0.08 + 0.25 * p) * W; cx, cy = ef["x"] * W, ef["y"] * H
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, int(200 * (1 - p))), width=6)
    return Image.alpha_composite(frame, ov)


# ----------------------------------------------------------------- render
def render(proj):
    rot = json.load(open(os.path.join(proj, "roteiro.json"), encoding="utf-8"))
    E = dict(ESTILO); E.update(rot.get("estilo", {}))
    if rot.get("formato", "9:16") == "16:9":
        E["W"], E["H"] = 1920, 1080
    W, H, FPS = E["W"], E["H"], E["FPS"]
    narr = achar_narracao(proj)
    voz = ler_audio(narr) if narr else np.zeros(int(SR * rot.get("duracao", 20)), np.float32)
    dur = len(voz) / SR + 0.6
    script = tempos_do_roteiro(rot, proj, len(voz) / SR)

    # limites de cada cena = primeira palavra dela
    cenas = rot["cenas"]
    for ci, c in enumerate(cenas):
        ws = [s for s in script if s[3] == ci]
        c["_ini"] = 0.0 if ci == 0 else (ws[0][1] - 0.04 if ws else cenas[ci - 1]["_ini"] + 1)
        c["_img"] = os.path.join(proj, c["imagem"]) if c.get("imagem") else None
    for ci, c in enumerate(cenas):
        c["_fim"] = cenas[ci + 1]["_ini"] if ci + 1 < len(cenas) else dur
        c["_tremor"] = []

    # ---- eventos (sticker, rotulo, destaque, sfx) presos a palavras
    def t_da_palavra(ci, gatilho, padrao):
        if gatilho is None:
            return padrao
        alvo = norm(gatilho)
        for s in script:
            if s[3] == ci and norm(s[0]).startswith(alvo):
                return s[1]
        return padrao

    eventos_sfx = []
    for ci, c in enumerate(cenas):
        if ci > 0 and c.get("corte_som", True):
            eventos_sfx.append((c["_ini"] - 0.08, "whoosh", 0.55))
        for ev in c.get("sfx", []):
            if isinstance(ev, str):
                ev = {"som": ev}
            t = t_da_palavra(ci, ev.get("na_palavra"), c["_ini"] + ev.get("apos", 0.15))
            eventos_sfx.append((t, ev["som"], ev.get("vol", 1.0)))
            if ev["som"] in ("impacto", "estalo") and ev.get("tremer", True):
                c["_tremor"].append(t - c["_ini"])
        if c.get("sticker"):
            c["_t_sticker"] = t_da_palavra(ci, c.get("sticker_na_palavra"), c["_ini"] + 0.1)
            eventos_sfx.append((c["_t_sticker"], "pop", 0.9))
        if c.get("rotulo"):
            c["_t_rotulo"] = t_da_palavra(ci, c.get("rotulo_na_palavra"), c["_ini"] + 0.3)
            eventos_sfx.append((c["_t_rotulo"], "ding", 0.5))
        if c.get("destaque"):
            c["_t_dest"] = t_da_palavra(ci, c["destaque"].get("na_palavra"), c["_ini"] + 0.3)
        for ef in c.get("efeitos", []):
            ef["_t0"] = t_da_palavra(ci, ef.get("na_palavra"), c["_ini"]) - c["_ini"]
            if ef.get("parar_na_palavra"):
                ef["_tstop"] = t_da_palavra(ci, ef["parar_na_palavra"], c["_ini"]) - c["_ini"]

    # ---- audio final
    total = np.zeros(int(SR * dur) + SR, np.float32)
    total[:len(voz)] += voz * E["vol_voz"]
    for t, nome, vol in eventos_sfx:
        y = sfx(nome, proj) * E["vol_sfx"] * vol
        i = max(0, int(t * SR)); total[i:i + len(y)] += y[:len(total) - i]
    mus = os.path.join(proj, "musica.mp3")
    if os.path.exists(mus):
        m = ler_audio(mus); m = np.tile(m, int(len(total) / len(m)) + 1)[:len(total)]
        total += m * E["vol_musica"]
    pico = np.abs(total).max()
    if pico > 0.98:
        total = total / pico * 0.98
    total = total[:int(SR * dur)]
    wav = os.path.join(proj, "_mix.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((total * 32767).astype(np.int16).tobytes())

    # ---- video
    saida = os.path.join(proj, rot.get("saida", "video.mp4"))
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", os.environ.get("PRESET", "veryfast"), "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", saida]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    rnd = random.Random(7)
    pal_imgs = {}
    nfr = int(dur * FPS)
    for fi in range(nfr):
        t = fi / FPS
        ci = max(i for i, c in enumerate(cenas) if c["_ini"] <= t + 1e-6)
        c = cenas[ci]; tl = t - c["_ini"]
        frame = quadro_fundo(c, tl, c["_fim"] - c["_ini"], W, H, rnd)
        frame = aplicar_efeitos(frame, c, t, tl, W, H)

        # destaque (circulo que se desenha em volta de um ponto)
        if c.get("destaque") and t >= c["_t_dest"]:
            d = c["destaque"]; p = min(1, (t - c["_t_dest"]) / 0.35)
            cx, cy, r = d["x"] * W, d["y"] * H, d.get("r", 0.16) * W
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(ov)
            dd.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * ease_in_out(p), fill=(255, 255, 255, 235), width=7)
            frame = Image.alpha_composite(frame, ov)

        # sticker (exclamacao) no topo
        if c.get("sticker") and t >= c["_t_sticker"]:
            k = c.get("_spr")
            if k is None:
                cor = E["vermelho"] if c.get("sticker_cor", "vermelho") == "vermelho" else E["amarelo"]
                k = c["_spr"] = caber(texto_contornado(c["sticker"].upper(), E["sticker_tam"], cor, 10, (255, 255, 255),
                                                       contorno2=6, cor2=(60, 20, 20)), W * 0.85)
            dt_ = t - c["_t_sticker"]
            esc = ease_out_back(dt_ / 0.3) if dt_ < 0.3 else 1 + 0.025 * math.sin(dt_ * 6)
            colar_central(frame, k, W / 2 + W * 0.05, H * c.get("sticker_y", E["sticker_y"]), esc, angulo=-6 + 2 * math.sin(dt_ * 3))

        # rotulo (termo tecnico) embaixo
        if c.get("rotulo") and t >= c["_t_rotulo"]:
            k = c.get("_rot")
            if k is None:
                cor = {"amarelo": E["amarelo"], "vermelho": E["coral"], "azul": E["azul"]}.get(c.get("rotulo_cor", "amarelo"), E["amarelo"])
                k = c["_rot"] = caber(texto_contornado(c["rotulo"].upper(), E["rotulo_tam"], cor, 7, (40, 25, 5)), W * 0.88)
            dt_ = t - c["_t_rotulo"]
            esc = ease_out_back(dt_ / 0.3) if dt_ < 0.3 else 1.0
            colar_central(frame, k, W / 2, H * c.get("rotulo_y", E["rotulo_y"]), esc, angulo=4)

        # legenda: a palavra que esta sendo falada
        atual = None
        for s in script:
            if s[1] - 0.02 <= t < s[2] + 0.12:
                atual = s
        if atual is None:  # mantem a ultima palavra durante pausas curtas
            ant = [s for s in script if s[2] <= t and t - s[2] < 0.5]
            atual = ant[-1] if ant else None
        if atual:
            marcada = "*" in atual[0]
            txt = re.sub(r"[\.,;:!?\"*]+$", "", atual[0].replace("*", ""))
            txt = txt[:1].upper() + txt[1:]
            chave_leg = (txt, marcada)
            if chave_leg not in pal_imgs:
                pal_imgs[chave_leg] = caber(texto_contornado(txt, E["legenda_tam"], E["azul"] if marcada else E["branco"],
                                                             E["legenda_contorno"], E["preto"]), W * 0.9)
            txt = chave_leg
            dt_ = t - atual[1]
            esc = 1.12 - 0.12 * ease_in_out(dt_ / 0.09) if dt_ < 0.09 else 1.0
            colar_central(frame, pal_imgs[txt], W / 2, H * E["legenda_y"], esc)

        ff.stdin.write(frame.convert("RGB").tobytes())
        if fi % (FPS * 5) == 0:
            print(f"  {t:5.1f}s / {dur:.1f}s", flush=True)
    ff.stdin.close(); ff.wait()
    os.remove(wav)
    print("OK ->", saida)


def exportar_sfx(proj):
    os.makedirs(os.path.join(proj, "_sfx_teste"), exist_ok=True)
    for n in SFX:
        y = sfx(n)
        with wave.open(os.path.join(proj, "_sfx_teste", n + ".wav"), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((y * 32767).astype(np.int16).tobytes())
    print("efeitos em", os.path.join(proj, "_sfx_teste"))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    {"alinhar": alinhar, "render": render, "sfx": exportar_sfx}[sys.argv[1]](sys.argv[2])
