"""Clona mensagens de um canal Telegram para outro.

Requisitos:
- Defina `API_ID`, `API_HASH`, `CANAL_ORIGEM` e `CANAL_DESTINO` em um arquivo `.env` na raiz do projeto.
- A sessão do Telethon será persistida em `sessao.session` (arquivo gerado automaticamente).

Uso:
- Execute o script e siga o prompt interativo para escolher quantas mensagens copiar.
- Respeite permissões e privacidade: obtenha autorização para reproduzir conteúdo quando necessário.

Este módulo é uma ferramenta simples de migração/backup de mensagens entre canais Telegram.
"""

from telethon import TelegramClient
from telethon.errors import FloodWaitError
import asyncio
import time
import os
import sys
from dotenv import load_dotenv # Biblioteca para carregar variáveis de ambiente
from tqdm import tqdm # Biblioteca para barra de progresso

# Carregar variáveis de ambiente a partir do arquivo .env (API_ID, API_HASH, CANAL_ORIGEM, CANAL_DESTINO)
load_dotenv()

# Configurações da API do Telegram (lidas do .env). Podem ser usernames (str) ou IDs (int):
api_id = os.getenv('API_ID')  # Carregar API ID do arquivo .env
api_hash = os.getenv('API_HASH')  # Carregar API Hash do arquivo .env
canal_origem = os.getenv('CANAL_ORIGEM')  # Nome de usuário ou ID do canal original
canal_destino = os.getenv('CANAL_DESTINO')  # Nome de usuário ou ID do seu canal privado

# Validação das variáveis de ambiente necessárias e instruções úteis se estiverem ausentes
missing = []
if not api_id:
    missing.append('API_ID')
if not api_hash:
    missing.append('API_HASH')
if not canal_origem:
    missing.append('CANAL_ORIGEM')
if not canal_destino:
    missing.append('CANAL_DESTINO')

if missing:
    print('Erro: variáveis de ambiente ausentes ou não configuradas:')
    for m in missing:
        print(f' - {m}')
    print('\nPor favor crie um arquivo .env na raiz do projeto com as variáveis abaixo (exemplo):')
    print('API_ID=123456')
    print('API_HASH=abcdef1234567890abcdef1234567890')
    print("CANAL_ORIGEM=@nome_do_canal_ou_ID")
    print("CANAL_DESTINO=@seu_canal_privado_ou_ID")
    print('\nVocê pode obter o `API_ID` e o `API_HASH` em https://my.telegram.org.')
    sys.exit(1)

# Garantir que API_ID seja inteiro (Telethon espera um int para api_id)
try:
    api_id = int(api_id)
except (ValueError, TypeError):
    print('Erro: API_ID inválido. Ele deve ser um número inteiro (ex: 123456).')
    print('Verifique seu arquivo .env e defina:')
    print('API_ID=123456')
    sys.exit(1)

# Converter `canal_origem` e `canal_destino` para inteiro quando vierem como IDs numéricos.
# Se forem usernames (ex: '@nome'), a conversão falhará e manteremos a string.
try:
    canal_origem = int(canal_origem)
except (ValueError, TypeError):
    pass

try:
    canal_destino = int(canal_destino)
except (ValueError, TypeError):
    pass

# Conectar ao Telegram e executar a rotina principal
async def main():
    """Principal rotina assíncrona.

    Conecta ao Telegram, valida acesso aos canais, baixa o histórico do canal de origem
    e reenvia as mensagens para o canal destino preservando a ordem cronológica.

    Observações:
    - Usa as variáveis globais `api_id`, `api_hash`, `canal_origem` e `canal_destino`.
    - Lida com `FloodWaitError` internamente para aguardar quando necessário.
    """

    # `async with` garante que a sessão seja corretamente aberta/fechada e que a sessão
    # seja persistida em disco (arquivo `sessao.session`).
    async with TelegramClient('sessao', api_id, api_hash) as client:
        print("Conectado ao Telegram!")

        try:
            # Verificar se conseguimos acessar o canal de origem (username ou ID)
            print(f"Tentando acessar canal origem: {canal_origem}")
            entity_origem = await client.get_entity(canal_origem)
            print(f"Canal origem encontrado: {entity_origem.title}")

            # Verificar se conseguimos acessar o canal de destino
            print(f"Tentando acessar canal destino: {canal_destino}")
            entity_destino = await client.get_entity(canal_destino)
            print(f"Canal destino encontrado: {entity_destino.first_name if hasattr(entity_destino, 'first_name') else 'Canal/Grupo'}")

        except Exception as e:
            print(f"Erro ao acessar canais: {e}")
            return

        # Obter mensagens do canal de origem
        # `limit=None` tentará buscar TODO o histórico — pode demorar e consumir memória/tempo.
        print("Baixando histórico de mensagens... (isso pode demorar dependendo do tamanho do canal)")
        messages = []
        try:
            # limit=None para buscar TODAS as mensagens.
            # Se quiser limitar, troque None por um número (ex: limit=100)
            async for message in client.iter_messages(canal_origem, limit=None):
                messages.append(message)
        except Exception as e:
            print(f"Erro ao obter mensagens: {e}")
            return
        
        # Inverte a lista para preservar ordem cronológica ao reenviar (do mais antigo ao mais recente)
        messages.reverse()
        total_mensagens = len(messages)
        print(f"Total de mensagens encontradas: {total_mensagens}")

        # Perguntar ao usuário quantas mensagens deseja copiar (interativo)
        num_to_copy = total_mensagens
        try:
            while True:
                escolha = input(f"Quantas mensagens copiar? (1-{total_mensagens}) ou Enter para todas: ")
                if escolha.strip() == "":
                    num_to_copy = total_mensagens
                    break
                try:
                    n = int(escolha)
                except ValueError:
                    print("Entrada inválida. Digite um número válido ou pressione Enter.")
                    continue
                if n <= 0:
                    print("Informe um número maior que zero ou pressione Enter para copiar todas.")
                    continue
                if n > total_mensagens:
                    print(f"O canal tem apenas {total_mensagens} mensagens. Informe até esse máximo.")
                    continue
                num_to_copy = n
                break
        except KeyboardInterrupt:
            print("\nOperação cancelada pelo usuário.")
            return

        if num_to_copy < total_mensagens:
            # Seleciona apenas as primeiras `num_to_copy` mensagens já em ordem cronológica
            messages = messages[:num_to_copy]

        print(f"Iniciando clonagem de {len(messages)} mensagens...")
        # Barra de progresso usando tqdm
        for message in tqdm(messages, desc="Copiando", unit="msg"):
            try:
                # Copiar mensagens para o canal destino
                # Se a mensagem contém mídia (fotos, vídeos, documentos), reenviamos com `send_file`.
                if message.media:  # Mensagens com mídia (fotos, vídeos, etc.)
                    await client.send_file(canal_destino, message.media, caption=message.text)
                elif message.text:  # Mensagens de texto (apenas se houver texto)
                    await client.send_message(canal_destino, message.text)
                else:
                    # Alguns tipos (ex: enquetes, stickers) podem não ser tratáveis aqui e são ignorados.
                    # Usamos `tqdm.write` para não corromper a barra de progresso ao imprimir.
                    # tqdm.write(f"Mensagem {message.id} ignorada (sem conteúdo suportado).")
                    continue

                # Pequena pausa para reduzir probabilidade de gatilho de limites do Telegram
                # time.sleep(0.1)

            except FloodWaitError as e:
                # FloodWaitError contém `seconds` — aguardamos o tempo recomendado pelo Telegram
                tqdm.write(f"Aguardando {e.seconds} segundos devido ao limite do Telegram...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                # Erros pontuais na cópia de uma mensagem são registrados e o processo continua
                tqdm.write(f"Erro ao copiar mensagem {message.id}: {e}")
        
        print("\nClonagem concluída com sucesso!")

if __name__ == '__main__':
    asyncio.run(main())
