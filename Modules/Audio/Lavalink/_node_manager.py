import os
import wavelink
import logging

logger = logging.getLogger("SamBot.LavalinkNodes")


async def setup_nodes(bot):
    """
    Inicializa e gerencia múltiplos servidores Lavalink.
    Faz o balanceamento de carga automático do Wavelink.
    """
    nodes = []

    local_host = os.getenv("LAVALINK_LOCAL_HOST", "127.0.0.1")
    local_port = os.getenv("LAVALINK_LOCAL_PORT", "2333")
    local_pass = os.getenv("LAVALINK_LOCAL_PASSWORD", "youshallnotpass")

    if local_host:
        nodes.append(
            wavelink.Node(
                identifier="LOCAL",
                uri=f"http://{local_host}:{local_port}",
                password=local_pass,
            )
        )
        logger.info(f"🎧 Node Local ({local_host}) engatilhado.")

    # Suporta múltiplos servidores separados por vírgula no .env
    online_hosts = os.getenv("LAVALINK_ONLINE_HOSTS", "")
    online_ports = os.getenv("LAVALINK_ONLINE_PORTS", "")
    online_passwords = os.getenv("LAVALINK_ONLINE_PASSWORDS", "")

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

        for i, host in enumerate(hosts):
            port = ports[i] if i < len(ports) else ports[0]
            pwd = passwords[i] if i < len(passwords) else passwords[0]

            protocol = "https" if port == "443" else "http"

            nodes.append(
                wavelink.Node(
                    identifier=f"ONLINE_{i+1}",
                    uri=f"{protocol}://{host}:{port}",
                    password=pwd,
                )
            )
            logger.info(f"☁️ Node Online {i+1} ({host}) engatilhado.")

    if not nodes:
        logger.error(
            "🚨 Nenhum servidor Lavalink configurado! O módulo de música não vai funcionar."
        )
        return

    # O Wavelink.Pool cuida de balancear a carga entre todos os nodes adicionados!
    await wavelink.Pool.connect(client=bot, nodes=nodes)
    logger.info(f"🚀 {len(nodes)} Node(s) Lavalink conectado(s) ao Pool de Carga!")
