"""
Shaaha v2.0 — Intelligent Meta-Dispatcher for Python
=====================================================
One import. Best backend. Always.
"""
import sys
import logging
from shaaha.importer import ShaahafFinder
from shaaha.environment import Environment

__version__ = "2.0.0"
__author__  = "Shaaha"
__license__ = "MIT"

logging.getLogger("shaaha").addHandler(logging.NullHandler())

_finder = ShaahafFinder()
if not any(isinstance(f, ShaahafFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _finder)

_env = Environment.probe()

try:
    from shaaha.plugins import PluginRegistry
    PluginRegistry().load_all()
except Exception:
    pass

suppress_warnings: bool = False

def configure(prefer_gpu=True, auto_install=False, log_level="WARNING", force_backend=None):
    from shaaha.router import Router
    logging.getLogger("shaaha").setLevel(getattr(logging, log_level.upper(), logging.WARNING))
    Router.configure(prefer_gpu=prefer_gpu, auto_install=auto_install, force_backend=force_backend or {})

def status() -> dict:
    from shaaha.router import Router
    from shaaha.brain import Brain
    brain = Brain()
    return {
        "version": __version__, "python": _env.python_version,
        "cuda_available": _env.cuda_available, "cuda_device": _env.cuda_device,
        "cpu_cores": _env.cpu_cores, "selected_backends": Router.selected_backends(),
        "brain_confidence": f"{brain.confidence()*100:.0f}%",
        "brain_summary": brain.summary(), "environment": _env.to_dict(),
    }

def available_backends(domain: str) -> list:
    from shaaha.registry import Registry
    return Registry.available_backends(domain)

def agent(task: str, api_key=None, save_report: bool = True) -> dict:
    """Run a natural language task. Example: shaaha.agent('load sales.csv and plot top 10')"""
    from shaaha.agent import agent as _agent
    return _agent(task, api_key=api_key, save_report=save_report)

def optimize_file(filepath: str, auto_apply: bool = False, use_llm: bool = True, api_key=None) -> dict:
    """Analyse and rewrite a Python script for speed. Example: shaaha.optimize_file('analysis.py')"""
    from shaaha.rewriter import optimize_file as _opt
    return _opt(filepath, auto_apply=auto_apply, use_llm=use_llm, api_key=api_key)

def reset_learning():
    """Clear all adaptive brain learning data."""
    from shaaha.brain import Brain
    Brain().reset()

def explain(filepath: str, output=None, api_key=None) -> str:
    """Explain all library choices in plain English. Example: shaaha.explain('script.py')"""
    from shaaha.explainer import explain as _explain
    return _explain(filepath, output=output, api_key=api_key)

def dashboard(port: int = 7842, open_browser: bool = True):
    """Open benchmark dashboard. Example: shaaha.dashboard()"""
    from shaaha.dashboard import dashboard as _dash
    _dash(port=port, open_browser=open_browser)

def register_backend(domain: str, name: str, import_path: str, priority: int = 80, tags=None, gpu_preferred: bool = False):
    """Register a custom backend. Example: shaaha.register_backend('dataframe','vaex','vaex',priority=88)"""
    from shaaha.plugins import register_backend as _reg
    _reg(domain, name, import_path, priority, tags, gpu_preferred)

def list_backends(domain=None):
    """List all backends. Example: shaaha.list_backends() or shaaha.list_backends('math')"""
    from shaaha.plugins import list_backends as _list
    _list(domain)

def share_profile(output_path=None) -> str:
    """Export learned profile for sharing."""
    from shaaha.collab import share_profile as _share
    return _share(output_path)

def import_profile(filepath: str, merge: bool = True):
    """Import a teammate's profile."""
    from shaaha.collab import import_profile as _imp
    _imp(filepath, merge=merge)

def sync(server_url: str, machine_id=None):
    """Sync with team server."""
    from shaaha.collab import sync as _sync
    _sync(server_url, machine_id)

def safe_mode(enabled: bool = True):
    """Enable output verification before backend switches. Example: shaaha.safe_mode(True)"""
    from shaaha.safety import safe_mode as _sm
    _sm(enabled)

def safe_call(domain: str, func_name: str, *args, **kwargs):
    """Call domain function with safety verification."""
    from shaaha.safety import safe_call as _sc
    return _sc(domain, func_name, *args, **kwargs)
