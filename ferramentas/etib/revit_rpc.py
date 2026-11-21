"""Cliente direto do plugin revit-mcp (porta 8080), para quando o servidor MCP (npx) não conecta.
Uso: python revit_rpc.py arquivo.cs [timeout_s]   -> executa o C# (mesmo contrato do send_code_to_revit)"""
import socket, json, sys, time

def send(code, timeout=600, host='localhost', port=8080):
    req = {'jsonrpc': '2.0', 'method': 'send_code_to_revit',
           'params': {'code': code, 'parameters': []}, 'id': str(int(time.time() * 1000))}
    s = socket.create_connection((host, port), timeout=10)
    s.settimeout(timeout)
    s.sendall(json.dumps(req).encode('utf-8'))
    buf = b''
    while True:
        chunk = s.recv(65536)
        if not chunk: break
        buf += chunk
        try:
            r = json.loads(buf.decode('utf-8')); break
        except ValueError:
            continue
    s.close()
    if 'error' in r and r['error']: raise RuntimeError(r['error'].get('message', r['error']))
    return r.get('result')

if __name__ == '__main__':
    code = open(sys.argv[1], encoding='utf-8').read()
    t = float(sys.argv[2]) if len(sys.argv) > 2 else 600
    t0 = time.time()
    res = send(code, t)
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(res, ensure_ascii=False, indent=1) if not isinstance(res, str) else res)
    print('[%.1fs]' % (time.time() - t0), file=sys.stderr)
