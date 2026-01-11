"""
Script de Clonagem de Canais Telegram.

Este script permite clonar mensagens (texto e mídia) de um canal, grupo ou usuário (origem)
para outro (destino) de forma interativa. Utiliza a biblioteca Telethon para interagir
com a API do Telegram.

Funcionalidades:
- Autenticação via API_ID e API_HASH (pode usar arquivo .env ou entrada manual).
- Listagem e seleção interativa de diálogos (canais/chats) recentes.
- Filtragem de mensagens por data de início.
- Seleção de quantidade específica de mensagens a copiar.
- Barra de progresso visual (tqdm).
- Tratamento automático de limites de taxa (FloodWaitError).

Dependências:
- telethon
- python-dotenv
- tqdm

Uso:
    python script-verificado.py
"""

from telethon import TelegramClient
from telethon.errors import FloodWaitError
import asyncio
import os
import datetime
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

def ask_env_or_input(var_name, prompt_text, is_int=False):
    """
    Obtém um valor de configuração a partir de variável de ambiente ou entrada do usuário.

    Verifica se existe um arquivo .env e se a variável está definida nele.
    Caso contrário, solicita o valor via terminal.

    Args:
        var_name (str): O nome da variável de ambiente a ser buscada.
        prompt_text (str): O texto a ser exibido no prompt se a entrada manual for necessária.
        is_int (bool, optional): Se True, converte o valor de retorno para inteiro. Padrão é False.

    Returns:
        Union[str, int]: O valor da configuração (como string ou inteiro).
    """
    env_val = os.getenv(var_name)
    # Se existir um arquivo .env, usar os valores definidos nele automaticamente.
    # Só perguntar ao usuário se a variável estiver ausente no .env.
    if os.path.exists('.env') and env_val:
        return int(env_val) if is_int else env_val
    # Caso não haja .env ou a variável esteja ausente, pedir entrada ao usuário.
    while True:
        v = input(f"{prompt_text}: ").strip()
        if v == "":
            print("Valor obrigatório. Tente novamente.")
            continue
        if is_int:
            try:
                return int(v)
            except ValueError:
                print("Informe um número inteiro válido.")
                continue
        return v

async def choose_dialog(client, prompt):
    """
    Lista os diálogos recentes e permite ao usuário selecionar uma origem/destino.

    Oferece uma interface interativa para escolher entre os últimos 200 diálogos
    listados ou inserir manualmente um username/ID.

    Args:
        client (TelegramClient): A instância do cliente Telethon conectada.
        prompt (str): Mensagem descritiva para orientar a escolha do usuário (ex: "Origem").

    Returns:
        entity: A entidade do Telegram (User, Chat ou Channel) selecionada, ou None se cancelado.
    """
    dialogs = await client.get_dialogs(limit=200)
    print(f"\n{prompt}: escolha pelo número ou digite um @username ou ID manualmente.")
    for i, d in enumerate(dialogs, start=1):
        ent = d.entity
        name = getattr(ent, "title", None) or getattr(ent, "first_name", None) or getattr(ent, "username", None) or str(getattr(ent, "id", ""))
        username = getattr(ent, "username", None)
        print(f"{i:3d}. {name}  (id={getattr(ent, 'id', None)}{f', @{username}' if username else ''})")
    escolha = input("Número ou @username/ID: ").strip()
    if escolha == "":
        return None
    if escolha.isdigit():
        idx = int(escolha) - 1
        if 0 <= idx < len(dialogs):
            return dialogs[idx].entity
        else:
            print("Índice fora do intervalo.")
            return await choose_dialog(client, prompt)
    try:
        maybe_id = int(escolha)
        return await client.get_entity(maybe_id)
    except ValueError:
        return await client.get_entity(escolha)

async def main():
    """
    Função principal que orquestra o processo de clonagem.

    Steps:
    1. Carrega credenciais (API_ID, API_HASH).
    2. Conecta ao Telegram via Telethon.
    3. Solicita seleção de origem e destino.
    4. Filtra mensagens por data.
    5. Baixa o histórico de mensagens.
    6. Clona as mensagens para o destino respeitando limites de taxa.
    """
    # --- 1. Configuração e Autenticação ---
    api_id = ask_env_or_input("API_ID", "Informe API_ID", is_int=True)
    api_hash = ask_env_or_input("API_HASH", "Informe API_HASH")

    async with TelegramClient('sessao', api_id, api_hash) as client:
        print("Conectado ao Telegram!")

        try:
            # --- 2. Seleção de Diálogos (Origem e Destino) ---
            origem_ent = await choose_dialog(client, "Selecionar canal/usuário de origem")
            if origem_ent is None:
                print("Origem não selecionada. Saindo.")
                return
            destino_ent = await choose_dialog(client, "Selecionar canal/usuário destino")
            if destino_ent is None:
                print("Destino não selecionado. Saindo.")
                return
        except Exception as e:
            print(f"Erro ao listar/selecionar diálogos: {e}")
            return

        print(f"Origem selecionada: {getattr(origem_ent, 'title', getattr(origem_ent, 'first_name', getattr(origem_ent, 'username', origem_ent)))}")
        print(f"Destino selecionado: {getattr(destino_ent, 'title', getattr(destino_ent, 'first_name', getattr(destino_ent, 'username', destino_ent)))}")

        # --- 3. Definição de Filtros (Data) ---
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

        # Tenta obter o total de mensagens para exibir barra de progresso precisa
        total_to_fetch = None
        try:
            from telethon.tl.functions.messages import GetHistoryRequest
            history = await client(GetHistoryRequest(peer=origem_ent, offset_id=0, offset_date=None,
                                                     add_offset=0, limit=0, max_id=0, min_id=0, hash=0))
            total_to_fetch = getattr(history, 'count', None)
        except Exception:
            total_to_fetch = None

        # --- 4. Obtenção do Histórico ---
        pbar = tqdm(total=total_to_fetch, desc="Baixando", unit="msg") if total_to_fetch else tqdm(desc="Baixando", unit="msg")
        try:
            async for message in client.iter_messages(origem_ent, limit=None):
                # Filtra mensagens anteriores à data escolhida, se houver
                if start_date:
                    if not hasattr(message, 'date') or message.date is None:
                        pbar.update(1)
                        continue
                    try:
                        msg_date = message.date.date()
                    except Exception:
                        pbar.update(1)
                        continue
                    if msg_date < start_date:
                        break # Como as mensagens vêm da mais recente para a mais antiga, podemos parar aqui
                messages.append(message)
                pbar.update(1)
        except Exception as e:
            pbar.close()
            print(f"Erro ao obter mensagens: {e}")
            return
        finally:
            pbar.close()

        # Inverte a lista para que a ordem de clonagem seja cronológica (antiga -> nova)
        messages.reverse()
        total_mensagens = len(messages)
        if start_date:
            print(f"Total de mensagens desde {start_date.isoformat()}: {total_mensagens}")
        else:
            print(f"Total de mensagens baixadas: {total_mensagens}")

        # --- 5. Seleção de Quantidade ---
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
            # Como a lista foi invertida para ordem cronológica (Antiga -> Nova),
            # selecionar os primeiros 'num_to_copy' elementos significa clonar as mensagens
            # mais antigas a partir da data de início selecionada.
            messages = messages[:num_to_copy]

        print(f"Iniciando clonagem de {len(messages)} mensagens...")
        # --- 6. Loop de Clonagem ---
        for message in tqdm(messages, desc="Copiando", unit="msg"):
            try:
                # Se tiver mídia, usa send_file, senão send_message
                if message.media:
                    await client.send_file(destino_ent, message.media, caption=message.text)
                elif message.text:
                    await client.send_message(destino_ent, message.text)
                else:
                    continue
            except FloodWaitError as e:
                # Tratamento de Rate Limit do Telegram
                tqdm.write(f"Aguardando {e.seconds} segundos devido ao limite do Telegram...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                tqdm.write(f"Erro ao copiar mensagem {getattr(message, 'id', '??')}: {e}")

        print("\nClonagem concluída com sucesso!")

if __name__ == '__main__':
    asyncio.run(main())
