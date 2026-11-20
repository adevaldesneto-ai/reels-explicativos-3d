# Reels explicativos em 3D — skill para o Claude

Transforme qualquer tema em um **vídeo explicativo vertical no estilo reels**: imagens 3D low-poly de desenho animado, narração animada por IA, **legenda gigante palavra por palavra**, figurinhas, rótulos com os termos técnicos, animações e efeitos sonoros feitos em Python.

Você pede ao Claude: *"faz um vídeo explicativo de como acontece um infarto"*. Ele:
1. escreve uma **explicação completa e revisada** do tema (com fontes);
2. transforma a explicação num roteiro no formato **"construir do zero"** (monta o órgão, a máquina ou o sistema peça por peça e depois mostra o que dá errado);
3. gera a **narração** e as **imagens** com a API do Google Gemini (com a sua chave);
4. **anima tudo em Python** (câmera, batidas, fluxo, rachaduras, setas, legendas, figurinhas, sons) e entrega o `video.mp4`.

Funciona para qualquer matéria: medicina, biologia, física, história, economia...

## O que tem aqui

```
video-explicativo-3d.zip         ← a skill pronta para instalar no Claude
skill/video-explicativo-3d/      ← a mesma skill, aberta (para ler e editar)
  SKILL.md                       ← instruções que o Claude segue
  scripts/motor.py               ← alinha a voz e renderiza o vídeo
  scripts/gemini_media.py        ← gera narração e imagens pela API do Gemini
exemplos/infarto/                ← projeto completo (explicação, roteiro, prompts)
exemplos/avc/                    ← outro projeto completo
assets/                          ← coloque aqui o seu mascote (mascote.png)
```

## Requisitos

- **Claude com acesso a um terminal no seu computador**: Claude Code, ou o app do Claude com uma ferramenta de terminal/arquivos conectada.
- **Python 3.9+** e **ffmpeg**.
- Bibliotecas: `python -m pip install -r requirements.txt`
- **Chave da API do Google Gemini** (https://aistudio.google.com → API keys), com crédito ativo.
- Fonte recomendada: [Montserrat ExtraBold](https://fonts.google.com/specimen/Montserrat) em `skill/video-explicativo-3d/scripts/fontes/Montserrat-ExtraBold.ttf`. Sem ela, usa uma fonte grossa do sistema.

### Guardar a chave com segurança (nunca em arquivo do projeto)
- **Windows (PowerShell):** `setx GEMINI_API_KEY "sua-chave"` e abra um terminal novo.
- **macOS/Linux:** `export GEMINI_API_KEY="sua-chave"` (coloque no `~/.zshrc` ou `~/.bashrc`).

## Instalar a skill

**No app do Claude (claude.ai / desktop):** baixe o arquivo [`video-explicativo-3d.zip`](video-explicativo-3d.zip) (abra o link e clique no botão de download) e envie em **Configurações → Capacidades → Skills → Enviar skill**.

**No Claude Code:** copie a pasta para as suas skills:
```bash
cp -r skill/video-explicativo-3d ~/.claude/skills/
```

## Usar

Peça ao Claude, por exemplo:
> Faz um vídeo explicativo de como funciona a vacina, em linguagem simples.

Na primeira vez, ele combina com você um **mascote original** (o personagem que reage nas cenas) e salva em `assets/mascote.png`.

Custo de referência na API do Gemini: cerca de US$ 1–2 por vídeo de ~2 minutos (~25 imagens + narração). Confira os preços atuais do Google.

### Usar os scripts sem o Claude
```bash
cd exemplos/infarto
python ../../skill/video-explicativo-3d/scripts/gemini_media.py narrar narracao_gemini.json AUDIOS --voz Puck --estilo estilo_voz.txt
cp AUDIOS/cena01.wav narracao.wav
python ../../skill/video-explicativo-3d/scripts/gemini_media.py imagens prompts_gemini.json img --formato 9:16
python ../../skill/video-explicativo-3d/scripts/motor.py alinhar .
python ../../skill/video-explicativo-3d/scripts/motor.py render .
```

## Observações

- Os exemplos tratam de saúde em linguagem leiga e **não substituem orientação médica**. Em emergência, ligue para o serviço de emergência do seu país (no Brasil, 192).
- Nos exemplos, algumas cenas reaproveitam imagens de outro projeto e algumas imagens foram recortadas depois de geradas; por isso há números de cena sem prompt.
- Se usar um vídeo de outro criador como referência, copie só o estilo e o ritmo, nunca o personagem, a voz ou o texto.

## Licença

Código e textos sob a licença [MIT](LICENSE). Feito por Adevaldes com o Claude.
