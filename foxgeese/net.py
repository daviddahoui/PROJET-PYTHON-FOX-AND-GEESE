"""Mode en ligne entre amis, via un relais MQTT public (aucun serveur à héberger).

Principe :
  - l'hôte se connecte à un relais public et génère un code de partie (ex. "K7QM4") ;
  - son ami tape ce code : les deux jeux s'abonnent au même « salon » sur le relais ;
  - chaque coup est envoyé sous forme de petit message JSON, et les deux jeux
    appliquent les mêmes règles (rules.py) pour obtenir le même plateau.

Les messages transitent par un relais public : ils ne contiennent que des coups
de jeu et des pseudos, rien de personnel.
"""

from __future__ import annotations

import json
import queue
import random
import ssl
import threading
import time
import uuid

import paho.mqtt.client as mqtt

try:
    import certifi
    _CA_FILE = certifi.where()
except ImportError:  # pragma: no cover
    _CA_FILE = None

PROTOCOL = 1
TOPIC_ROOT = "fox-and-geese-dd/v1"

# Relais publics gratuits. Pour chacun : TCP direct, puis WebSocket sécurisé (port
# ouvert sur la plupart des réseaux d'école/entreprise) en secours.
BROKERS = [
    ("broker.emqx.io", [("tcp", 1883, None), ("websockets", 8084, "/mqtt")]),
    ("broker.hivemq.com", [("tcp", 1883, None), ("websockets", 8884, "/mqtt")]),
    ("test.mosquitto.org", [("tcp", 1883, None), ("websockets", 8081, None)]),
]

# Alphabet sans caractères ambigus (pas de 0/O, 1/I/L)
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LEN = 5

HEARTBEAT = 2.0      # secondes entre deux « ping »
TIMEOUT = 15.0       # sans nouvelles depuis ce délai => adversaire déconnecté


def make_code(broker_index: int, rng: random.Random | None = None) -> str:
    """4 caractères aléatoires + 1 caractère qui indique quel relais est utilisé."""
    rng = rng or random.SystemRandom()
    head = "".join(rng.choice(ALPHABET) for _ in range(CODE_LEN - 1))
    tail = rng.choice([c for i, c in enumerate(ALPHABET) if i % len(BROKERS) == broker_index])
    return head + tail


def normalize_code(text: str) -> str:
    return "".join(ch for ch in text.upper() if ch.isalnum())


def code_is_valid(code: str) -> bool:
    return len(code) == CODE_LEN and all(ch in ALPHABET for ch in code)


def broker_of(code: str) -> int:
    return ALPHABET.index(code[-1]) % len(BROKERS)


class NetSession:
    """Connexion à un salon de partie. Tout se passe dans un thread réseau ;
    le jeu lit les événements reçus avec poll() à chaque image."""

    def __init__(self, role: str, name: str, code: str | None = None):
        assert role in ("host", "guest")
        self.role = role
        self.name = name[:16] or "Joueur"
        self.code = code
        self.client_id = uuid.uuid4().hex[:12]
        self.events: queue.Queue = queue.Queue()
        self.peer: str | None = None          # identifiant de l'adversaire une fois appairé
        self.peer_name: str | None = None
        self.connected = False
        self.closed = False
        self._client: mqtt.Client | None = None
        self._last_seen = 0.0
        self._seq = 0
        self._seen_seq: set[tuple[str, int]] = set()
        self._thread = threading.Thread(target=self._run, daemon=True)

    # --- API utilisée par le jeu ---------------------------------------------

    def start(self) -> None:
        self._thread.start()

    def poll(self) -> list[dict]:
        out = []
        while True:
            try:
                out.append(self.events.get_nowait())
            except queue.Empty:
                break
        if self.peer and not self.closed and time.monotonic() - self._last_seen > TIMEOUT:
            self._last_seen = float("inf")
            out.append({"t": "lost"})
        return out

    def send(self, msg: dict) -> None:
        if not self._client or self.closed:
            return
        self._seq += 1
        msg = dict(msg, v=PROTOCOL, id=self.client_id, seq=self._seq)
        self._client.publish(self._topic, json.dumps(msg), qos=1)

    def close(self) -> None:
        if self.closed:
            return
        try:
            if self._client and self.connected:
                self.send({"t": "bye"})
                time.sleep(0.15)
                self._client.disconnect()
            if self._client:
                self._client.loop_stop()
        except Exception:
            pass
        self.closed = True

    # --- Coulisses réseau -------------------------------------------------------

    @property
    def _topic(self) -> str:
        return f"{TOPIC_ROOT}/{self.code}"

    def _candidates(self):
        if self.role == "guest":
            order = [broker_of(self.code)]
        else:
            order = list(range(len(BROKERS)))
        for bi in order:
            host, transports = BROKERS[bi]
            for transport, port, path in transports:
                yield bi, host, transport, port, path

    def _try_connect(self, host, transport, port, path) -> mqtt.Client | None:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                             client_id=f"fg-{self.client_id}", transport=transport)
        if transport == "websockets":
            client.ws_set_options(path=path or "/mqtt")
            client.tls_set(ca_certs=_CA_FILE, tls_version=ssl.PROTOCOL_TLS_CLIENT)
        # Message « d'adieu » publié par le relais si on disparaît brutalement
        client.will_set(self._topic, json.dumps({"t": "bye", "id": self.client_id, "v": PROTOCOL}))
        done = threading.Event()
        result = {}

        def on_connect(c, userdata, flags, rc, props=None):
            result["rc"] = rc
            if not rc.is_failure:
                c.subscribe(self._topic, qos=1)   # aussi après une reconnexion automatique
            done.set()

        client.on_connect = on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect
        try:
            client.connect_async(host, port, keepalive=20)
            client.loop_start()
        except Exception:
            return None
        if not done.wait(6) or getattr(result.get("rc"), "is_failure", True):
            try:
                client.loop_stop()
                client.disconnect()
            except Exception:
                pass
            return None
        return client

    def _run(self) -> None:
        client = None
        for bi, host, transport, port, path in self._candidates():
            if self.closed:
                return
            if self.role == "host":
                self.code = make_code(bi)
            self.events.put({"t": "status", "text": f"Connexion au relais {bi + 1}…"})
            client = self._try_connect(host, transport, port, path)
            if client:
                break
        if not client:
            self.events.put({"t": "error", "text": "Impossible de joindre le relais en ligne. "
                                                   "Vérifie ta connexion internet."})
            return

        self._client = client
        self.connected = True
        self._last_seen = time.monotonic()
        if self.role == "host":
            self.events.put({"t": "hosting", "code": self.code})
        else:
            self.events.put({"t": "status", "text": "Recherche de la partie…"})

        tries = 0
        while not self.closed:
            if self.role == "guest" and not self.peer:
                # On frappe à la porte jusqu'à ce que l'hôte réponde
                if tries >= 8:
                    self.events.put({"t": "error", "text": "Aucune partie trouvée avec ce code."})
                    return
                self.send({"t": "join", "name": self.name})
                tries += 1
            elif self.peer:
                self.send({"t": "ping"})
            time.sleep(HEARTBEAT)

    def _on_disconnect(self, client, userdata, flags, rc, props=None):
        if not self.closed and self.peer:
            self.events.put({"t": "status", "text": "Connexion instable, reconnexion…"})

    def _on_message(self, client, userdata, message):
        try:
            msg = json.loads(message.payload.decode("utf-8"))
        except Exception:
            return
        sender = msg.get("id")
        if sender == self.client_id or msg.get("v") != PROTOCOL:
            return
        seq = msg.get("seq")
        if seq is not None:
            if (sender, seq) in self._seen_seq:
                return                       # doublon (QoS 1 peut renvoyer un message)
            self._seen_seq.add((sender, seq))
        t = msg.get("t")

        if self.peer is None:
            if self.role == "host" and t == "join":
                self.peer, self.peer_name = sender, str(msg.get("name", "Ami"))[:16]
                self._last_seen = time.monotonic()
                self.send({"t": "welcome", "to": sender, "name": self.name})
                self.events.put({"t": "joined", "name": self.peer_name})
            elif self.role == "guest" and t == "welcome" and msg.get("to") == self.client_id:
                self.peer, self.peer_name = sender, str(msg.get("name", "Ami"))[:16]
                self._last_seen = time.monotonic()
                self.events.put({"t": "joined", "name": self.peer_name})
            elif self.role == "guest" and t == "full" and msg.get("to") == self.client_id:
                self.events.put({"t": "error", "text": "Cette partie est déjà complète."})
            return

        if sender != self.peer:
            if self.role == "host" and t == "join":
                self.send({"t": "full", "to": sender})
            return
        self._last_seen = time.monotonic()
        if t != "ping":
            self.events.put(msg)
