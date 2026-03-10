import socket, threading, select, sys, signal
import paramiko

HOST='100.119.68.81'
USER='root'
PASSWORD='763ed7b2'
LOCAL_HOST='127.0.0.1'
LOCAL_PORT=18880
REMOTE_HOST='127.0.0.1'
REMOTE_PORT=18800

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASSWORD, timeout=12, banner_timeout=12, auth_timeout=12)
transport = client.get_transport()
if transport is None:
    raise SystemExit('no transport')

lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
lsock.bind((LOCAL_HOST, LOCAL_PORT))
lsock.listen(100)

stop = False

def handle(conn):
    chan = transport.open_channel('direct-tcpip', (REMOTE_HOST, REMOTE_PORT), conn.getpeername())
    while True:
        r, _, _ = select.select([conn, chan], [], [], 60)
        if conn in r:
            data = conn.recv(65535)
            if not data:
                break
            chan.sendall(data)
        if chan in r:
            data = chan.recv(65535)
            if not data:
                break
            conn.sendall(data)
    try:
        chan.close()
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass

def serve():
    while True:
        try:
            conn, _ = lsock.accept()
        except Exception:
            break
        threading.Thread(target=handle, args=(conn,), daemon=True).start()

def shutdown(*args):
    try:
        lsock.close()
    except Exception:
        pass
    try:
        client.close()
    except Exception:
        pass
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)
print(f'TUNNEL_READY {LOCAL_HOST}:{LOCAL_PORT} -> {HOST}:{REMOTE_HOST}:{REMOTE_PORT}', flush=True)
serve()
