"""
Tergite Quantum Runner
Run:  python app.py
Open: http://localhost:5001
"""
import threading, queue, json, traceback
from flask import Flask, request, jsonify, Response, send_from_directory

app = Flask(__name__, static_folder='static')

# ── Serve UI ─────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


# ── List available backends ───────────────────────────────
@app.route('/backends')
def list_backends():
    api_key = request.args.get('api_key', '')
    api_url = request.args.get('api_url', '').strip().rstrip('/') + '/'
    try:
        from tergite import Tergite
        provider = Tergite.use_provider_account(service_name='local', url=api_url, token=api_key)
        names = [b.name for b in provider.backends()]
        return jsonify({'backends': names})
    except Exception as e:
        return jsonify({'error': f'{type(e).__name__}: {e}'})


# ── Diagnose connection ───────────────────────────────────
@app.route('/diagnose')
def diagnose():
    api_key = request.args.get('api_key', '')
    api_url = request.args.get('api_url', '').strip().rstrip('/') + '/'
    import requests as req
    results = []
    for url in [api_url, api_url + 'backends', api_url + 'v1/backends']:
        try:
            r = req.get(url, headers={'Authorization': f'Bearer {api_key}', 'token': api_key}, timeout=8)
            results.append({'url': url, 'status': r.status_code, 'body': r.text[:400]})
        except Exception as e:
            results.append({'url': url, 'status': 'ERR', 'body': str(e)})
    return jsonify({'results': results})


# ── Build circuit ─────────────────────────────────────────
def build_circuit(mode, n, custom_code=None):
    import qiskit.circuit as circuit_mod

    if mode == 'init':
        qc = circuit_mod.QuantumCircuit(n, n)
        qc.measure(list(range(n)), list(range(n)))

    elif mode == 'ent':
        qc = circuit_mod.QuantumCircuit(n, n)
        qc.h(0)
        for i in range(n - 1):
            qc.cx(i, i + 1)
        qc.measure(list(range(n)), list(range(n)))

    elif mode == 'rnd':
        qc = circuit_mod.QuantumCircuit(n, n)
        for i in range(n):
            qc.h(i)
        qc.measure(list(range(n)), list(range(n)))

    elif mode == 'cust':
        if not custom_code:
            raise ValueError("No custom code provided.")
        import qiskit.circuit as circuit
        namespace = {'circuit': circuit}
        exec(custom_code, namespace)  # noqa
        qc = namespace.get('qc')
        if qc is None:
            raise ValueError("Custom code must assign a QuantumCircuit to variable 'qc'.")

    else:
        raise ValueError(f"Unknown mode: {mode}")

    return qc


# ── Run job (streamed via SSE) ────────────────────────────
def run_job(payload, q):
    def emit(msg, cls=''):
        q.put({'type': 'log', 'msg': msg, 'cls': cls})

    try:
        mode        = payload.get('mode', 'ent')
        n           = int(payload.get('qubits', 5))
        api_key     = payload.get('api_key', '')
        api_url     = payload.get('api_url', '').strip().rstrip('/') + '/'
        backend_name= payload.get('backend', '')
        shots       = int(payload.get('shots', 1024))
        timeout     = int(payload.get('timeout', 600))
        custom_code = payload.get('custom_code', '')

        emit('Importing Qiskit…', 'info')
        import qiskit.compiler as compiler

        emit('Importing Tergite SDK…', 'info')
        from tergite import Tergite, Job

        # Build circuit
        mode_labels = {'init': 'Initialize', 'ent': 'GHZ Entangle', 'rnd': 'Random H', 'cust': 'Custom'}
        emit(f'Building {mode_labels.get(mode, mode)} circuit ({n} qubits)…', 'info')
        qc = build_circuit(mode, n, custom_code)
        emit(f'Circuit ready: {qc.num_qubits}q / depth {qc.depth()}', 'ok')

        # Connect
        emit(f'Connecting to {api_url}…', 'info')
        provider = Tergite.use_provider_account(service_name='local', url=api_url, token=api_key)
        emit('Provider connected.', 'ok')

        # Try get_backend, fall back to filtering backends() list
        try:
            backend = provider.get_backend(backend_name)
        except Exception as e1:
            emit(f'get_backend failed ({e1}), trying backends()…', 'warn')
            all_backends = provider.backends()
            available = [b.name for b in all_backends]
            emit(f'Available backends: {available}', 'info')
            matched = [b for b in all_backends if b.name == backend_name]
            if not matched:
                raise ValueError(
                    f"Backend '{backend_name}' not found. Available: {available}"
                )
            backend = matched[0]
        backend.set_options(shots=shots)
        emit(f'Backend: {backend.name}   shots={shots}', 'info')

        # Compile
        emit('Transpiling…', 'info')
        tc = compiler.transpile(qc, backend=backend, optimization_level=0)
        emit('Scheduling pulses…', 'info')
        schedules = compiler.schedule(tc, backend=backend)
        emit('Compiled.', 'ok')

        # Run
        emit('Submitting job to quantum processor…', 'step')
        job: Job = backend.run([schedules], meas_level=2, meas_return='single')
        emit('Job submitted — waiting for results…', 'ok')
        job.wait_for_final_state(timeout=timeout)

        # Results
        result = job.result()
        counts = result.get_counts()
        total  = sum(counts.values())
        top    = max(counts, key=counts.get)
        emit(f'Done. {len(counts)} distinct states / {total} shots', 'ok')
        emit(f'Top state: {top} ({counts[top]})', 'ok')

        q.put({'type': 'done', 'counts': counts, 'qubits': n})

    except ImportError as e:
        q.put({'type': 'error', 'msg': f'Missing library: {e}  →  pip install qiskit tergite'})
    except Exception as e:
        traceback.print_exc()
        q.put({'type': 'error', 'msg': f'{type(e).__name__}: {e}'})


@app.route('/run')
def run_sse():
    try:
        payload = json.loads(request.args.get('payload', '{}'))
    except Exception:
        payload = {}

    q = queue.Queue()

    def stream():
        t = threading.Thread(target=run_job, args=(payload, q), daemon=True)
        t.start()
        while True:
            try:
                msg = q.get(timeout=3)
                yield f'data: {json.dumps(msg)}\n\n'
                if msg['type'] in ('done', 'error'):
                    break
            except queue.Empty:
                yield f'data: {json.dumps({"type":"heartbeat"})}\n\n'

    return Response(stream(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


if __name__ == '__main__':
    print('\n  ╔══════════════════════════════╗')
    print('  ║   Tergite Quantum Runner     ║')
    print('  ╚══════════════════════════════╝')
    print('\n  Open: http://localhost:5001\n')
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
