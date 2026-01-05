# 🎯 Telegram Channel Cloner

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Telethon](https://img.shields.io/badge/Telethon-1.24+-blue.svg)
![Status](https://img.shields.io/badge/Status-Funcional-success.svg)

> 🚀 Clone canais do Telegram (mensagens, fotos, vídeos e arquivos) para o seu próprio canal ou grupo privado.

## 📋 Visão Geral

Este script em Python permite copiar todo o histórico de um canal do Telegram (origem) para outro (destino). Ele preserva a ordem cronológica das mensagens e suporta textos e mídias.

## ✨ Funcionalidades

- 🔄 Clona mensagens de texto, imagens, vídeos e documentos.
- 📝 Preserva a ordem cronológica (envia da mais antiga para a mais nova).
- 📊 Barra de progresso visual para acompanhar a clonagem.
- 🛡️ Tratamento automático de limites do Telegram (FloodWait).
- ⚙️ Configuração simples via arquivo `.env`.

## 🚀 Como Usar

### 1. Pré-requisitos

Você precisa ter o **Python** instalado no seu computador.

### 2. Instalação

1. Baixe ou clone este repositório.
2. Abra o terminal na pasta do projeto.
3. Instale as dependências necessárias:

```bash
pip install -r requirements.txt
```

### 3. Configuração

1. Crie um arquivo chamado `.env` na RAIZ do projeto (você pode copiar o `.env.example` e renomear).
2. Abra o arquivo `.env` e preencha com seus dados:

```env
API_ID=seu_api_id
API_HASH=seu_api_hash
CANAL_ORIGEM=@canal_que_quero_copiar
CANAL_DESTINO=@meu_canal_destino
```

> **Como conseguir API_ID e API_HASH?**
> Acesse [my.telegram.org](https://my.telegram.org), faça login e vá em "API development tools".

### 4. Executando

No terminal, execute:

```bash
python script-verificado.py
```

Siga as instruções na tela. Na primeira vez, será necessário fazer login com seu número de telefone. Se sua conta tiver 2FA (verificação de dois fatores), além do código de confirmação será necessário colocar a senha.

## 🔒 Permissões e limitações do Telegram

- Para clonar canais privados, sua conta precisa ter acesso (ser membro ou convidado) ao canal origem.
- Para postar no canal destino, sua conta deve ter permissão de postagem ou ser administrador do canal/grupo destino.
- Mensagens reenviadas pelo script aparecem como novas mensagens e podem perder metadados (reações, contadores de visualizações, etc.).
- O Telegram aplica limites de taxa; operações em massa podem resultar em `FloodWait` e pausas automáticas.

## 🧠 Aviso sobre memória e tempo

- Por padrão o script usa `limit=None` e tenta baixar todo o histórico do canal, o que pode consumir muita memória e tempo em canais grandes.
- Em canais com milhares de mensagens, recomenda-se usar limites (`limit=<n>`), copiar por lotes ou executar em uma máquina com memória suficiente.
- Monitore o uso de memória/CPU durante execuções longas e considere interromper e reiniciar por partes se necessário.

## 💾 Sessão do Telethon

- O arquivo `sessao.session` é gerado na raiz do projeto e guarda a sessão da sua conta; não compartilhe este arquivo nem o envie para repositórios públicos.
- Para revogar acesso, remova o arquivo e/ou revogue a sessão nas configurações da sua conta em https://my.telegram.org.
- Adicione `sessao.session` e o arquivo `.env` ao `.gitignore` para evitar vazamento de credenciais.

## 📄 Licença e distribuição

- Este repositório inclui um arquivo `LICENSE` que determina os termos de uso, cópia e distribuição. Consulte-o para informações legais detalhadas.
- Redistribuição e uso comercial do código devem respeitar os termos da licença incluída no projeto.

## ⚠️ Aviso Legal

Esta ferramenta é para uso pessoal e educacional. Respeite os direitos autorais e os termos de serviço do Telegram. Não utilize para clonar conteúdo protegido sem permissão.