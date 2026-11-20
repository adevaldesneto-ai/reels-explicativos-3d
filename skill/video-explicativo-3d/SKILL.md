---
name: video-explicativo-3d
description: Produz vídeos explicativos curtos no estilo reels (vertical 9:16), com imagens 3D low-poly de desenho animado, legenda gigante palavra por palavra, figurinhas, rótulos, animações e efeitos sonoros feitos em Python, e narração animada por IA. Use quando o usuário pedir um "vídeo explicativo", "reel educativo" ou "vídeo explicando como X funciona", de qualquer matéria.
---

# Vídeo explicativo em 3D (estilo reels, animado em Python)

Esta skill transforma qualquer tema (como funciona o coração, por que o céu é azul, como nasce um vulcão, o que é inflação...) em um vídeo vertical curto, no estilo dos reels educativos que viralizam: personagem e objetos em **3D low-poly de desenho animado**, cortes rápidos, narração animada e informal, **legenda gigante palavra por palavra**, figurinhas de exclamação, rótulos com os termos técnicos e efeitos sonoros.

**O que vale acima de tudo é a QUALIDADE DA EXPLICAÇÃO.** Não existe duração padrão: o vídeo dura o que a explicação completa precisar (em geral 60 a 120 s). Nunca corte uma etapa para encurtar. Só respeite uma duração se o usuário pedir uma.

**Divisão do trabalho:**
- **Gerador de IA** (por padrão, Google Gemini com a chave do próprio usuário) cria a narração e as imagens-base.
- **Python** (o `scripts/motor.py` desta skill) anima tudo: câmera, batidas, fluxo, rachaduras, setas, partículas, escurecimento, alarmes, legendas, figurinhas, sons e mixagem. Toda cena leva pelo menos um efeito animado: nunca entregue imagens paradas só com zoom.

Arquivos desta skill:
- `scripts/motor.py`: alinha a voz com o texto e renderiza o vídeo.
- `scripts/gemini_media.py`: gera narração e imagens pela API do Gemini (chave em `GEMINI_API_KEY`).
- `exemplos/`, no repositório: projetos completos para copiar a estrutura.

---

## 0. Preparar o ambiente (só na primeira vez)

Precisa de um computador com terminal (Claude Code, ou o app do Claude com acesso a um terminal/pasta local).

1. **Python 3.9+** e **ffmpeg** no PATH (`ffmpeg -version` deve funcionar).
2. Bibliotecas: `python -m pip install pillow numpy faster-whisper truststore`
3. **Fonte** (recomendada): baixe a Montserrat ExtraBold (Google Fonts, licença OFL) para `scripts/fontes/Montserrat-ExtraBold.ttf`. Sem ela, o motor usa Arial Black ou outra fonte grossa do sistema.
4. **Chave do Gemini:** crie em https://aistudio.google.com (API keys) e guarde **só** numa variável de ambiente:
   - Windows: `setx GEMINI_API_KEY "sua-chave"` e abra um terminal novo.
   - macOS/Linux: `export GEMINI_API_KEY="sua-chave"` (coloque no `~/.zshrc` ou `~/.bashrc`).
   - **Nunca** peça a chave no chat, nunca a mostre, nunca a grave em arquivo do projeto.
5. Teste: `python scripts/gemini_media.py simular narrar <arquivo>` mostra o pedido sem gastar.

Custo de referência: um vídeo de ~2 min com ~25 imagens fica em torno de US$ 1–2 na API do Gemini (confira os preços atuais). Diga a estimativa em uma linha antes de gerar.

Se o usuário preferir outro gerador (ElevenLabs, OpenAI, um conector de imagem do Claude), use-o: o motor só precisa de `narracao.wav` (ou `.mp3`) e `img/cenaXX.jpg`.

---

## 1. O formato que faz o vídeo funcionar: "construir do zero"

O narrador **monta** o objeto ou sistema como um engenheiro, resolvendo um problema por vez. Cada ciclo tem 4 batidas:
1. **"Mas..."**: um PROBLEMA concreto e engraçado ("mas ele entorta pro lado e você beija a calçada").
2. **"Então você..."**: a SOLUÇÃO com analogia do dia a dia (fitas, mangueiras, cadarço, almofadas, portão).
3. **"Esses são os..."**: o NOME TÉCNICO, que vira rótulo amarelo.
4. Quando couber, **o que acontece quando falha** (rótulo vermelho).

Fecho: "Parabéns, agora você entende ___!" + gancho do próximo vídeo ("Qual eu monto no próximo? Comenta aí!").

**Para processos, doenças, falhas e desastres:** primeiro CONSTRUA o normal em 3–5 ciclos (por que cada peça existe), depois "agora vamos quebrar": a cadeia do que dá errado, passo a passo; depois os sinais, o que fazer, as soluções e a prevenção.

### Ritmo (guia, não duração)
- ~2,7–3 palavras por segundo; frases de 3 a 8 palavras.
- Corte de cena a cada 1,5–2,5 s: o mesmo modelo 3D visto de ângulos diferentes, intercalado com o **mascote reagindo** a cada 3–4 cenas (assusta, cai, comemora, fica tonto).
- Uma figurinha a cada 3–5 cenas; um rótulo a cada termo técnico novo.
- Rótulos: **amarelo** = termo técnico; **azul** = detalhe ou analogia ("MOLINHA", "3x VOCÊ"); **vermelho** = falha, lesão ou perigo.
- Legenda: uma palavra por vez; números e ênfases em **azul** (`*palavra*` no roteiro).

### Estilo visual e sonoro (já programado no motor)
| Elemento | Como é |
| --- | --- |
| Formato | Vertical 9:16, 1080x1920, 30 fps (`"formato": "16:9"` para horizontal) |
| Visual | 3D low-poly estilo jogo de celular, cores quentes e pastel, luz suave, fundo simples. Sem texto dentro das imagens. |
| Legenda | Uma palavra por vez, branca com contorno preto grosso, embaixo (73% da altura), com "pulo" ao aparecer. |
| Figurinha | Exclamação curta vermelha com contorno branco, inclinada, no topo, entrada elástica + pop. Nunca cobrindo rosto. |
| Rótulo | Logo abaixo da legenda (84%), amarelo/azul/vermelho + "ding". Textos longos encolhem sozinhos. |
| Sons | Whoosh em todo corte; pop na figurinha; ding no rótulo; impacto + tremor em quedas; estalo quando algo rompe; boing/escorrega em momentos cômicos. |

**Originalidade:** se o usuário mandar um vídeo de referência de outro criador, use só o estilo e o ritmo. Não copie o personagem, a voz, o texto nem a marca dele.

### Mascote
Cada canal tem o seu. Na primeira vez, combine com o usuário um mascote original em 3D low-poly (nome curto, cabelo, roupa marcante, expressões exageradas). Gere uma imagem dele, peça aprovação e salve em `assets/mascote.png`. Daí em diante, todo prompt com o mascote começa pelo nome dele (o "gatilho") e usa essa imagem como referência, para o personagem sair sempre igual.

---

## 2. Primeiro: a explicação (antes de qualquer roteiro)

Antes de pensar em cenas, escreva `explicacao.md` na pasta do projeto: o texto-base completo, em linguagem simples mas tecnicamente correta.
1. **O que é**, em uma frase.
2. **Como funciona normalmente**, passo a passo, cada peça e por que ela existe.
3. **O que dá errado / o que muda**: a cadeia de eventos na ordem, sem pular elos (se o tema tiver isso).
4. **Como se percebe** (sinais, sintomas, efeitos) e por quê.
5. **O que fazer** (soluções, tratamento, prevenção, aplicação prática), quando couber.
6. **Tabela de termos**: termo técnico | analogia | onde entra no vídeo.
7. **Fontes** consultadas.

Regras:
- **Precisão obrigatória.** Simplificar sim, errar não. Pesquise o que não tiver certeza (livros-texto, diretrizes oficiais, artigos). Use o material do usuário quando houver.
- **Profundidade:** quem assiste deve sair entendendo o MECANISMO, não só o nome. Se uma frase não explica um "porquê", falta coisa.
- **Temas de saúde:** inclua quando procurar ajuda (ex.: número de emergência do país do público) e não dê doses de remédio. Em segurança, finanças ou direito, nada de recomendação individual.
- Mostre um resumo da explicação, a duração estimada e o custo; espere o "ok", a não ser que o usuário tenha mandado fazer direto.

---

## 3. O roteiro (derivado da explicação)

- Transforme cada item das seções 2–5 da explicação em pelo menos um ciclo "Mas / Então você / Esses são". No fim, confira que nenhum passo ficou de fora.
- Fala com "você", tom de amigo, bem-humorado. Primeiro a analogia, depois o termo técnico.
- GANCHO nos primeiros 2 s, já entrando na construção ("Você vai montar um coração. E depois... vai quebrar ele!").
- Onomatopeias e reações ("Crec!", "Tombou!", "Nhac!") viram figurinhas.
- Números: por extenso na narração ("um nove dois"), em algarismos no roteiro (`*192*`).
- Sem dados de pessoas reais.

---

## 4. Pasta do projeto e roteiro.json

Pasta: `<pasta de vídeos>/<tema-sem-acento>/` com `explicacao.md`, `roteiro.json`, `narracao_gemini.json`, `estilo_voz.txt`, `prompts_gemini.json`, `img/` e, depois, `narracao.wav` e `video.mp4`.

Cada cena = 1 imagem + 3 a 6 palavras de fala (1,5–2,5 s). A soma dos `texto` (sem os asteriscos) deve ser a narração inteira, na ordem.

```json
{
  "titulo": "Infarto",
  "formato": "9:16",
  "cenas": [
    {"imagem": "img/cena11.jpg", "texto": "até que um dia, a casquinha racha!", "movimento": "parado",
     "efeitos": [{"tipo": "rachadura", "x": 0.41, "y": 0.44, "na_palavra": "racha"},
                 {"tipo": "particulas", "x": 0.41, "y": 0.44, "na_palavra": "racha", "n": 22}],
     "sticker": "Crec!", "sticker_na_palavra": "racha",
     "sfx": [{"som": "estalo", "na_palavra": "racha"}]},
    {"imagem": "img/cena05.jpg", "texto": "e gasta uns *vinte* por cento do oxigênio!", "movimento": "zoom_in",
     "rotulo": "Esfomeado", "rotulo_cor": "azul", "rotulo_na_palavra": "vinte"}
  ]
}
```

Campos de cada cena:
- `imagem`, `texto` (obrigatórios). `*palavra*` sai azul na legenda.
- `movimento`: `zoom_in` | `zoom_out` | `pan_esq` | `pan_dir` | `sobe` | `desce` | `parado` (varie; use `parado` quando um efeito precisa ficar alinhado a um ponto da imagem).
- `foco`: `[x, y]` (0–1 da imagem) ponto para onde a câmera aponta.
- `efeitos`: animações (seção 7).
- `sticker`, `sticker_na_palavra`, `sticker_cor` (`vermelho` | `amarelo`), `sticker_y` (padrão 0.20; use 0.08 quando o rosto estiver no topo).
- `rotulo`, `rotulo_na_palavra`, `rotulo_cor` (`amarelo` | `azul` | `vermelho`), `rotulo_y` (padrão 0.84).
- `destaque`: `{x, y, r, na_palavra}`, círculo branco que se desenha.
- `sfx`: lista de `{"som", "na_palavra", "vol"}`: `whoosh`, `pop`, `ding`, `impacto`, `estalo`, `boing`, `escorrega`, `tique`. `impacto`/`estalo` tremem a tela (`"tremer": false` desliga). Pop, ding e whoosh já são automáticos.
- `corte_som: false` desliga o whoosh daquele corte.
- `na_palavra` = começo da palavra, sem acento e sem asterisco ("coagulo", "192").

**Coordenadas:** a imagem cobre o quadro com folga de 22%. Com `parado` e foco no centro, um ponto (ix, iy) da imagem aparece em x ≈ 0,5 + 1,18·(ix − 0,5), y ≈ 0,5 + 1,18·(iy − 0,5). Olhe as imagens antes de posicionar efeitos.

---

## 5. Narração (Gemini)

1. `narracao_gemini.json`: `[["01", "narração inteira, sem asteriscos"]]`. Ponto = pausa curta; "!" = ênfase; reticências só para suspense. Acima de ~2 min de fala, divida em 2–3 itens e junte os WAVs com ffmpeg (concat).
2. `estilo_voz.txt` (padrão):
   > Narre em português do Brasil como um criador jovem de reels educativos de sucesso: animado, rápido, divertido e muito claro, como um amigo explicando algo surpreendente. Energia alta do começo ao fim, ênfase forte nas exclamações, pausas curtíssimas entre as frases, nada de tom de locutor de rádio, nada lento ou solene.

   Acrescente como ler siglas difíceis (ex.: `Leia "AVC" como "á-vê-cê"`). Para outro idioma, troque a primeira frase.
3. Rodar (voz padrão **Puck**; o usuário pode escolher outra das vozes prontas do Gemini):
   ```
   python <skill>/scripts/gemini_media.py narrar narracao_gemini.json AUDIOS --voz Puck --estilo estilo_voz.txt
   ```
   Copie `AUDIOS/cena01.wav` para `narracao.wav` e confira a duração com `ffprobe -v error -show_entries format=duration -of csv=p=0 narracao.wav`.

## 6. Imagens (Gemini)

1. `prompts_gemini.json`:
   ```json
   {"style": "Vertical 9:16 portrait image. Low-poly 3D cartoon render, like a cute mobile game, faceted geometric shapes, soft warm studio lighting, pastel colors, simple background, cinematic close framing, main subject in the upper and middle area, the whole frame filled with the same scene down to the bottom edge. No text, no letters, no numbers, no watermark.",
    "referencia": "assets/mascote.png",
    "gatilho": "<NomeDoMascote>",
    "prompts": {"01": "<NomeDoMascote>, ...", "02": "a cute low-poly 3D cartoon human heart, ..."}}
   ```
   Prompts em inglês. Objetos e anatomia corretos e reconhecíveis. Para ganhar ritmo sem gastar demais, gere um **modelo-base** (o órgão, a máquina, o lugar) e variações (ângulo, close, peça nova, peça quebrada) e reaproveite cada imagem em 2–3 cenas seguidas, com `movimento`/`foco` diferentes.
2. Rodar (~15 s por imagem):
   ```
   python <skill>/scripts/gemini_media.py imagens prompts_gemini.json img --formato 9:16
   ```
   Refaça só as ruins: `... imagens prompts_gemini.json img --formato 9:16 04 07`.
3. Monte uma folha de conferência e OLHE antes de seguir: `ffmpeg -v error -y -i img/cena%02d.jpg -vf "scale=200:-1,tile=8x4" -frames:v 1 _imgs.png`. Refaça: anatomia ou objeto errado, texto na imagem, mascote diferente. Se uma imagem vier com uma faixa vazia embaixo, recorte com ffmpeg (`crop=iw:ih*0.76:0:0`).

---

## 7. Animações em Python (campo `efeitos`)

Coordenadas relativas ao quadro (0–1). `na_palavra` define quando começa.

| tipo | O que faz | Parâmetros | Use para |
| --- | --- | --- | --- |
| `pulsar` | Câmera "bate" no ritmo tum-tum | `bpm` (80), `forca` (0.035) | Coração, tensão, relógio; bpm alto = urgência |
| `fluxo` | Partículas vermelhas correndo de (x0,y0) a (x1,y1) | `largura`, `n`, `vel`, `tamanho`, `parar_na_palavra`, `limite` | Sangue, água, trânsito; com `parar_na_palavra` o fluxo trava |
| `seta` | Seta branca balançando | `x`, `y`, `direcao` (baixo/cima/esq/dir), `tamanho` | Força, peso, "aqui", direção |
| `rachadura` | Rachadura que se desenha | `x`, `y` | Algo rompendo, quebrando |
| `particulas` | Explosão de fragmentos | `x`, `y`, `n`, `cor` [r,g,b] | Ruptura, estouro, impacto |
| `escurecer` | Mancha que cresce | `x`, `y`, `r`, `dur`, `cor`, `alpha` | Área morrendo, contaminação, sombra |
| `alarme` | Tela piscando em vermelho | `alpha` | Emergência, perigo |
| `brilho` | Anéis que se expandem | `x`, `y` | Dor, sinal, energia, "olha aqui" |

A ordem importa: efeitos são desenhados na ordem da lista (ponha `alarme` antes de `escurecer` para a mancha ficar por cima). Se precisar de uma animação nova, crie um novo `tipo` em `aplicar_efeitos` no `motor.py` e documente aqui.

---

## 8. Montar, conferir e entregar

```
cd <pasta do projeto>
python <skill>/scripts/motor.py alinhar .   # palavras.json (faster-whisper; baixa o modelo na 1ª vez)
python <skill>/scripts/motor.py render .    # video.mp4
```
`alinhar` deve dizer "N palavras alinhadas" com N ≈ palavras do roteiro. O render leva ~1 min a cada 25 s de vídeo; use timeout longo. Em processos longos, rode em segundo plano e acompanhe o log.

**Conferência obrigatória:** folhas de 24 em 24 s até o fim:
```
ffmpeg -v error -y -ss 0 -t 24 -i video.mp4 -vf "fps=1,scale=160:-1,tile=8x3" -frames:v 1 _c000.png
```
Verifique: legenda embaixo e legível; figurinha sem cobrir rosto; rótulo inteiro; efeitos no lugar certo; corte a cada 1,5–2,5 s; nenhum passo da explicação faltando. Corrija o `roteiro.json` e renderize de novo.

**Entrega:** caminho do vídeo + duração em uma linha. Ofereça salvar numa pasta de nuvem do usuário (Drive, OneDrive) para ele assistir no celular.

---

## 9. Checklist final

- [ ] `explicacao.md` completa e revisada, com fontes.
- [ ] Roteiro "construir do zero" cobrindo todos os passos; gancho e fecho.
- [ ] Duração definida pela explicação.
- [ ] Cortes a cada 1,5–2,5 s, mascote a cada 3–4 cenas, rótulos amarelo/azul/vermelho, figurinhas.
- [ ] Narração e imagens geradas; chave nunca exibida; custo informado antes.
- [ ] Toda cena com animação Python; legenda embaixo.
- [ ] Vídeo inteiro conferido nas folhas.
