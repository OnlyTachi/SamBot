# Modules/Audio/Lavalink/_node_manager.py
import logging
import os
from Brain.Core.NetworkManager import NetworkManager
from Core.ConfigLoader import AppConfig
import wavelink

logger = logging.getLogger("SamBot.LavalinkNodes")
session = NetworkManager.get_aio_session()


async def test_node_health(uri: str) -> bool:
    """Realiza um teste rápido de HTTP HEAD/GET para validar porta e SSL."""
    try:
        async with session.get(uri, timeout=3.0, ssl=False) as resp:
            return resp.status in [200, 400, 401, 404]
    except Exception:
        return False


async def setup_nodes(bot):
    nodes = []
    music_mode = AppConfig.get("MUSIC_SOURCE_MODE", "ONLINE").strip().upper()
    logger.info(f"Modo de busca musical ativo: {music_mode}")

    # 1. Modo LOCAL: Conecta no Lavalink local (container docker ou host)
    if music_mode == "LOCAL":
        local_host = AppConfig.get("LAVALINK_HOST", "lavalink")
        local_port = AppConfig.get("LAVALINK_PORT", "2333")
        local_password = AppConfig.get("LAVALINK_PASSWORD", "youshallnotpass")
        uri = f"http://{local_host}:{local_port}"

        if await test_node_health(uri):
            nodes.append(
                wavelink.Node(
                    identifier="LOCAL_1",
                    uri=uri,
                    password=local_password,
                )
            )
            logger.info(f"Node Local Lavalink ({uri}) engatilhado com sucesso.")
        else:
            # Tenta fallback para localhost se 'lavalink' falhar
            fallback_uri = f"http://127.0.0.1:{local_port}"
            if await test_node_health(fallback_uri):
                nodes.append(
                    wavelink.Node(
                        identifier="LOCAL_1",
                        uri=fallback_uri,
                        password=local_password,
                    )
                )
                logger.info(
                    f"Node Local Lavalink ({fallback_uri}) engatilhado com sucesso."
                )
            else:
                logger.error(
                    f"Falha de ping no nó Lavalink Local em {uri} e {fallback_uri}."
                )

    # 2. Modo ONLINE: Conecta nos nós remotos públicos/privados
    elif music_mode == "ONLINE":
        online_hosts = AppConfig.get("LAVALINK_ONLINE_HOSTS", "")
        online_ports = AppConfig.get("LAVALINK_ONLINE_PORTS", "")
        online_passwords = AppConfig.get("LAVALINK_ONLINE_PASSWORDS", "")

        if online_hosts:
            hosts = [h.strip() for h in online_hosts.split(",")]
            ports = (
                [p.strip() for p in online_ports.split(",")]
                if online_ports
                else ["443"] * len(hosts)
            )
            passwords = (
                [p.strip() for p in online_passwords.split(",")]
                if online_passwords
                else ["youshallnotpass"] * len(hosts)
            )
            ssl_ports = ["443", "8443", "2053", "2083", "2096"]

            for i, host in enumerate(hosts):
                port = ports[i] if i < len(ports) else ports[0]
                pwd = passwords[i] if i < len(passwords) else passwords[0]
                protocol = "https" if port in ssl_ports else "http"
                uri = f"{protocol}://{host}:{port}"

                if await test_node_health(uri):
                    nodes.append(
                        wavelink.Node(
                            identifier=f"ONLINE_{i+1}",
                            uri=uri,
                            password=pwd,
                        )
                    )
                    logger.info(f"Node Online {i+1} ({host}) engatilhado com sucesso.")
                else:
                    logger.warning(
                        f"Node Online {i+1} ({host}) falhou no teste de ping e foi"
                        " ignorado."
                    )

    if not nodes:
        logger.error(
            "  Nenhum servidor Lavalink configurado/ativo! O módulo de música não"
            " vai funcionar."
        )
        return

    await wavelink.Pool.connect(client=bot, nodes=nodes)
    logger.info(f"  {len(nodes)} Node(s) Lavalink conectado(s) ao Pool de Carga!")
