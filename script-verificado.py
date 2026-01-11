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
import datetime
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

        # Obter mensagens do canal de origem (com opção de filtro por data)
        print("Baixando histórico de mensagens... (isso pode demorar dependendo do tamanho do canal)")

        # Perguntar data inicial ao usuário antes de baixar o histórico
        start_date = None
        while True:
            entrada = input("Data inicial (AAAA-MM-DD) ou Enter para todas: ").strip()
            if entrada == "":
                break
            try:
                start_date = datetime.datetime.strptime(entrada, "%Y-%m-%d").date()
                break
            except ValueError:
                print("Formato inválido. Use AAAA-MM-DD.")

        messages = []

        # Tentar obter contagem total para barra de progresso (opcional)
        total_to_fetch = None
        try:
            from telethon.tl.functions.messages import GetHistoryRequest
            history = await client(GetHistoryRequest(peer=entity_origem, offset_id=0, offset_date=None,
                                                     add_offset=0, limit=0, max_id=0, min_id=0, hash=0))
            total_to_fetch = getattr(history, 'count', None)
        except Exception:
            total_to_fetch = None

        pbar = tqdm(total=total_to_fetch, desc="Baixando", unit="msg") if total_to_fetch else tqdm(desc="Baixando", unit="msg")
        try:
            # iter_messages retorna do mais novo para o mais antigo — interromper ao encontrar mensagens mais antigas que a data solicitada
            async for message in client.iter_messages(canal_origem, limit=None):
                if start_date:
                    # algumas mensagens podem não ter atributo date — pular nesses casos
                    if not hasattr(message, 'date') or message.date is None:
                        pbar.update(1)
                        continue
                    try:
                        msg_date = message.date.date()
                    except Exception:
                        pbar.update(1)
                        continue
                    if msg_date < start_date:
                        # como já estamos indo para o passado, podemos parar — economiza requisições
                        break

                messages.append(message)
                pbar.update(1)
        except Exception as e:
            pbar.close()
            print(f"Erro ao obter mensagens: {e}")
            return
        finally:
            pbar.close()
        
        # Inverte a lista para preservar ordem cronológica ao reenviar (do mais antigo ao mais recente)
        messages.reverse()
        total_mensagens = len(messages)
        if start_date:
            print(f"Total de mensagens desde {start_date.isoformat()}: {total_mensagens}")
        else:
            print(f"Total de mensagens baixadas: {total_mensagens}")

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
