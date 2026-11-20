# -*- coding: utf-8 -*-
"""
Narracao (voz) e imagens com a API do Google Gemini, usando a SUA chave.

A chave e lida da variavel de ambiente GEMINI_API_KEY (nunca coloque a chave em arquivos).
  Windows (PowerShell):  setx GEMINI_API_KEY "sua-chave"   (abra um terminal novo depois)
  macOS/Linux:           export GEMINI_API_KEY="sua-chave"

Uso:
  python gemini_media.py narrar  narracao_gemini.json AUDIOS --voz Puck --estilo estilo_voz.txt
  python gemini_media.py imagens prompts_gemini.json img --formato 9:16 [01 05 07]
  python gemini_media.py simular narrar|imagens <arquivo.json> ...   (mostra o pedido sem chamar a API)

Formatos dos arquivos:
  narracao_gemini.json -> [["01", "texto completo da narracao"], ["02", "..."]]
                          gera AUDIOS/cena01.wav, AUDIOS/cena02.wav ...
  prompts_gemini.json  -> {"style": "...", "prompts": {"01": "...", "02": "..."},
                           "referencia": "assets/mascote.png", "gatilho": "Ze"}
                          gera img/cena01.jpg, img/cena02.jpg ...
                          A imagem de "referencia" so e anexada aos prompts que comecam com o "gatilho".

Modelos (troque se o Google lancar outros):
  GEMINI_TTS_MODEL   (padrao: gemini-3.8-flash-tts)
  GEMINI_IMAGE_MODEL (padrao: gemini-3.1-flash-image)

Requisitos: Python 3.9+, pillow. Opcional: truststore (corrige erro de certificado SSL no Windows).
Licenca: MIT.
"""
import base64, io, json, os, sys, time, urllib.error, urllib.request, wave

try:  # usa os certificados do sistema (evita erro de SSL em alguns Windows)
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

API = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
MODELO_VOZ = os.environ.get("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
MODELO_IMG = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")


def chave():
    k = os.environ.get("GEMINI_API_KEY", "").strip()
    if not k:
        sys.exit("ERRO: defina a variavel de ambiente GEMINI_API_KEY com a sua chave do Google AI Studio.")
    return k


def chamar(modelo, corpo, tentativas=4):
    req = urllib.request.Request(API.format(modelo=modelo), data=json.dumps(corpo).encode("utf-8"),
                                 headers={"Content-Type": "application/json", "x-goog-api-key": chave()})
    for i in range(tentativas):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "ignore")
            if e.code in (429, 500, 502, 503, 504) and i < tentativas - 1:
                espera = 5 * (i + 1)
                print(f"  aviso: HTTP {e.code}, tentando de novo em {espera}s...", flush=True)
                time.sleep(espera)
                continue
            sys.exit(f"ERRO {e.code}: {msg[:800]}")


def partes_inline(resp):
    for cand in resp.get("candidates", []):
        for p in cand.get("content", {}).get("parts", []):
            if "inlineData" in p:
                yield p["inlineData"]


def salvar_audio(dados, mime, destino):
    if "wav" in (mime or "").lower():
        open(destino, "wb").write(dados)
        return
    taxa = 24000  # PCM 16-bit mono (padrao da API); le a taxa se vier no mime
    for pedaco in (mime or "").split(";"):
        if pedaco.strip().startswith("rate="):
            taxa = int(pedaco.split("=")[1])
    with wave.open(destino, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(taxa); w.writeframes(dados)


def narrar(arq, saida, voz="Puck", estilo_arq=None, simular=False):
    itens = json.load(open(arq, encoding="utf-8"))
    estilo = open(estilo_arq, encoding="utf-8").read().strip() if estilo_arq else ""
    os.makedirs(saida, exist_ok=True)
    print(f"modelo de voz: {MODELO_VOZ} | voz: {voz}")
    for chave_cena, texto in itens:
        prompt = (f"## Style: {estilo}\n## Transcript: {texto}" if estilo else texto)
        corpo = {"contents": [{"parts": [{"text": prompt}]}],
                 "generationConfig": {"responseModalities": ["AUDIO"],
                                      "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voz}}}}}
        if simular:
            print(json.dumps(corpo, ensure_ascii=False, indent=1)[:1500]); continue
        resp = chamar(MODELO_VOZ, corpo)
        audio = next(partes_inline(resp), None)
        if not audio:
            sys.exit(f"ERRO: a API nao devolveu audio para {chave_cena}: {json.dumps(resp)[:500]}")
        destino = os.path.join(saida, f"cena{chave_cena}.wav")
        salvar_audio(base64.b64decode(audio["data"]), audio.get("mimeType"), destino)
        print(f"ok cena{chave_cena}.wav", flush=True)


def imagem_b64(caminho):
    from PIL import Image
    im = Image.open(caminho).convert("RGB")
    im.thumbnail((1024, 1024))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def imagens(arq, saida, formato="9:16", so=None, simular=False):
    from PIL import Image
    cfg = json.load(open(arq, encoding="utf-8"))
    estilo, prompts = cfg.get("style", ""), cfg["prompts"]
    ref, gatilho = cfg.get("referencia"), cfg.get("gatilho")
    if ref and not os.path.isabs(ref):
        ref = os.path.join(os.path.dirname(os.path.abspath(arq)), ref)
    ref_b64 = imagem_b64(ref) if (ref and os.path.exists(ref) and not simular) else None
    os.makedirs(saida, exist_ok=True)
    print(f"modelo de imagem: {MODELO_IMG}")
    for k in sorted(prompts):
        if so and k not in so:
            continue
        texto = f"{prompts[k]}\n\n{estilo}".strip()
        partes = [{"text": texto}]
        usa_ref = bool(gatilho) and prompts[k].strip().lower().startswith(gatilho.lower())
        if usa_ref and ref_b64:
            partes.append({"inlineData": {"mimeType": "image/jpeg", "data": ref_b64}})
            partes[0]["text"] += f"\n\nThe attached image is the reference for the character called {gatilho}: keep the same character design."
        corpo = {"contents": [{"parts": partes}],
                 "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": formato}}}
        if simular:
            print(k, "| referencia:" , usa_ref, "|", texto[:300]); continue
        resp = chamar(MODELO_IMG, corpo)
        img = next(partes_inline(resp), None)
        if not img:
            print(f"AVISO: sem imagem para {k}: {json.dumps(resp)[:300]}"); continue
        im = Image.open(io.BytesIO(base64.b64decode(img["data"]))).convert("RGB")
        im.save(os.path.join(saida, f"cena{k}.jpg"), "JPEG", quality=92)
        print(f"ok cena{k}.jpg", flush=True)


def main(argv):
    simular = False
    if argv and argv[0] == "simular":
        simular, argv = True, argv[1:]
    if len(argv) < 3 or argv[0] not in ("narrar", "imagens"):
        print(__doc__); sys.exit(1)
    cmd, arq, saida, resto = argv[0], argv[1], argv[2], argv[3:]

    def opcao(nome, padrao):
        if nome in resto:
            i = resto.index(nome); v = resto[i + 1]; del resto[i:i + 2]; return v
        return padrao

    if cmd == "narrar":
        narrar(arq, saida, voz=opcao("--voz", "Puck"), estilo_arq=opcao("--estilo", None), simular=simular)
    else:
        formato = opcao("--formato", "9:16")
        imagens(arq, saida, formato=formato, so=set(resto) or None, simular=simular)


if __name__ == "__main__":
    main(sys.argv[1:])
