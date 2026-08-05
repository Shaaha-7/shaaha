"""
shaaha.dashboard — Layer 7: The Benchmark Dashboard
=====================================================
Opens a local web UI showing all operations, backend choices,
speed comparisons, and machine performance history.

shaaha.dashboard()
"""
from __future__ import annotations
import json
import logging
import threading
import webbrowser
from pathlib import Path
from typing import Optional

logger = logging.getLogger("shaaha.dashboard")

_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Shaaha Dashboard</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
       background:#0f1117;color:#e2e8f0;min-height:100vh}
  header{background:linear-gradient(135deg,#1a1a2e,#16213e);
         padding:24px 32px;border-bottom:1px solid #2d3748}
  header h1{font-size:1.8rem;font-weight:700;color:#fff}
  header p{color:#94a3b8;margin-top:4px}
  .badge{display:inline-block;background:#0f3460;color:#60a5fa;
         padding:2px 10px;border-radius:12px;font-size:.75rem;margin-left:8px}
  .container{max-width:1200px;margin:0 auto;padding:24px 32px}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-bottom:28px}
  .card{background:#1e2535;border:1px solid #2d3748;border-radius:12px;padding:20px}
  .card h3{font-size:.8rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px}
  .card .val{font-size:2rem;font-weight:700;color:#60a5fa}
  .card .sub{font-size:.8rem;color:#64748b;margin-top:4px}
  .section{background:#1e2535;border:1px solid #2d3748;border-radius:12px;
            padding:24px;margin-bottom:20px}
  .section h2{font-size:1rem;font-weight:600;margin-bottom:16px;color:#e2e8f0}
  table{width:100%;border-collapse:collapse;font-size:.875rem}
  th{text-align:left;padding:8px 12px;background:#0f1117;color:#94a3b8;
     font-weight:500;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em}
  td{padding:10px 12px;border-top:1px solid #2d3748;color:#cbd5e1}
  tr:hover td{background:#ffffff08}
  .pill{display:inline-block;padding:2px 8px;border-radius:20px;font-size:.75rem;font-weight:500}
  .pill-green{background:#064e3b;color:#34d399}
  .pill-blue{background:#1e3a5f;color:#60a5fa}
  .pill-yellow{background:#451a03;color:#fbbf24}
  .bar-wrap{background:#0f1117;border-radius:4px;height:8px;width:100%;margin-top:6px}
  .bar{height:8px;border-radius:4px;background:linear-gradient(90deg,#3b82f6,#60a5fa);transition:width .6s}
  .confidence{font-size:2rem;font-weight:700;color:#34d399}
  .empty{color:#475569;text-align:center;padding:32px;font-size:.9rem}
  .domain-chip{display:inline-block;background:#1e3a5f;color:#93c5fd;
               padding:3px 10px;border-radius:6px;font-size:.75rem;margin-right:4px}
  .refresh{float:right;background:#2d3748;border:none;color:#94a3b8;
           padding:6px 14px;border-radius:8px;cursor:pointer;font-size:.8rem}
  .refresh:hover{background:#374151;color:#e2e8f0}
</style>
</head>
<body>
<header>
  <h1>🧠 Shaaha Dashboard <span class="badge">v2.0</span></h1>
  <p>Real-time backend intelligence & performance history</p>
</header>
<div class="container" id="app">Loading...</div>
<script>
async function load(){
  const r=await fetch('/api/data');
  const d=await r.json();
  const app=document.getElementById('app');

  const ops=d.operations||{};
  const keys=Object.keys(ops);
  const totalRuns=keys.reduce((s,k)=>s+ops[k].count,0);
  const domains=new Set(keys.map(k=>ops[k].domain));
  const conf=Math.round(d.confidence*100);

  let rows='';
  const sorted=keys.sort((a,b)=>ops[b].count-ops[a].count);
  for(const k of sorted){
    const o=ops[k];
    const timings=o.timings||[];
    const med=timings.length?timings.slice().sort((a,b)=>a-b)[Math.floor(timings.length/2)]:0;
    const best=timings.length?Math.min(...timings):0;
    const worst=timings.length?Math.max(...timings):0;
    const pct=totalRuns>0?Math.round(o.count/totalRuns*100):0;
    rows+=`<tr>
      <td><span class="domain-chip">${o.domain}</span></td>
      <td><strong>${o.backend}</strong></td>
      <td>${o.count} <div class="bar-wrap"><div class="bar" style="width:${pct}%"></div></div></td>
      <td>${med.toFixed(1)}ms</td>
      <td>${best.toFixed(1)}ms</td>
      <td>${worst.toFixed(1)}ms</td>
      <td><span class="pill ${timings.length>=5?'pill-green':'pill-yellow'}">${timings.length>=5?'Learned':'Learning'}</span></td>
    </tr>`;
  }

  let recs='';
  for(const r of (d.recommendations||[])){
    recs+=`<div style="padding:10px 0;border-top:1px solid #2d3748;color:#94a3b8">
      ⚡ ${r}</div>`;
  }

  const selected=d.selected_backends||{};
  let selRows='';
  for(const [dom,back] of Object.entries(selected)){
    selRows+=`<tr><td><span class="domain-chip">${dom}</span></td>
    <td>${back}</td>
    <td><span class="pill pill-green">Active</span></td></tr>`;
  }

  app.innerHTML=`
  <div class="grid">
    <div class="card"><h3>Total Operations</h3>
      <div class="val">${totalRuns}</div>
      <div class="sub">recorded this machine</div></div>
    <div class="card"><h3>Domains Learned</h3>
      <div class="val">${domains.size}</div>
      <div class="sub">of 9 total domains</div></div>
    <div class="card"><h3>Brain Confidence</h3>
      <div class="confidence">${conf}%</div>
      <div class="sub">${conf<40?'Still learning...':conf<80?'Getting smarter':'Highly optimised'}</div></div>
    <div class="card"><h3>Active Backends</h3>
      <div class="val">${Object.keys(selected).length}</div>
      <div class="sub">selected this session</div></div>
  </div>

  ${selRows?`<div class="section"><h2>🎯 Current Session Backends
    <button class="refresh" onclick="load()">↻ Refresh</button></h2>
    <table><thead><tr><th>Domain</th><th>Backend</th><th>Status</th></tr></thead>
    <tbody>${selRows}</tbody></table></div>`:''}

  <div class="section"><h2>📊 Performance History</h2>
  ${rows?`<table><thead><tr>
    <th>Domain</th><th>Backend</th><th>Runs</th>
    <th>Median</th><th>Best</th><th>Worst</th><th>Status</th>
  </tr></thead><tbody>${rows}</tbody></table>`
  :'<div class="empty">No operations recorded yet.<br>Run some shaaha code to see stats here.</div>'}
  </div>

  ${recs?`<div class="section"><h2>💡 Brain Recommendations</h2>${recs}</div>`:''}

  <div class="section"><h2>🖥️ Environment</h2>
  <table><thead><tr><th>Property</th><th>Value</th></tr></thead><tbody>
    <tr><td>Python</td><td>${d.env?.python||'-'}</td></tr>
    <tr><td>CUDA</td><td>${d.env?.cuda?'✅ Available':'❌ Not available'}</td></tr>
    <tr><td>CUDA Device</td><td>${d.env?.cuda_device||'N/A'}</td></tr>
    <tr><td>CPU Cores</td><td>${d.env?.cpu_cores||'-'}</td></tr>
    <tr><td>OS</td><td>${d.env?.os||'-'}</td></tr>
  </tbody></table></div>`;
}
load();
setInterval(load,10000);
</script>
</body></html>'''


def _build_app():
    """
    Construct the Flask app (routes + API) without binding a port.

    Split out from dashboard() so the dashboard's actual behaviour —
    the HTML shell and the /api/data payload shape — can be tested with
    Flask's test_client() instead of only being verifiable by eyeballing
    a real browser session.
    """
    from flask import Flask, jsonify

    app_flask = Flask("shaaha_dashboard")

    @app_flask.route("/")
    def index():
        from flask import Response
        return Response(_HTML, mimetype="text/html")

    @app_flask.route("/api/data")
    def api_data():
        from shaaha.brain import Brain
        from shaaha.router import Router
        from shaaha.environment import Environment

        brain  = Brain()
        env    = Environment.probe()
        summary = brain.summary()
        data   = brain._data

        ops_enriched = {}
        for k, v in data.get("operations", {}).items():
            timings = v.get("timings", [])
            ops_enriched[k] = {**v, "timings": timings}

        return jsonify({
            "operations":       ops_enriched,
            "confidence":       brain.confidence(),
            "recommendations":  summary.get("recommendations", []),
            "selected_backends": Router.selected_backends(),
            "env": {
                "python":      env.python_version,
                "cuda":        env.cuda_available,
                "cuda_device": env.cuda_device,
                "cpu_cores":   env.cpu_cores,
                "os":          env.os_name,
            },
        })

    return app_flask


def dashboard(port: int = 7842, open_browser: bool = True):
    """
    Launch the Shaaha benchmark dashboard on a local web server.

    Args:
        port:         local port (default 7842)
        open_browser: auto-open in default browser

    Example:
        import shaaha
        shaaha.dashboard()
    """
    try:
        app_flask = _build_app()
    except ImportError:
        print("[Shaaha] Dashboard requires Flask: pip install flask")
        return

    url = f"http://127.0.0.1:{port}"
    print(f"\n🚀 [Shaaha Dashboard] Running at {url}")
    print("   Press Ctrl+C to stop.\n")

    if open_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    import logging as _logging
    _logging.getLogger("werkzeug").setLevel(_logging.ERROR)
    app_flask.run(port=port, debug=False, use_reloader=False)
