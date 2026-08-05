"""
shaaha.collab — Layer 9: The Collaboration Layer
=================================================
Export/import machine learning profiles to share with teammates.

shaaha.share_profile()          # export to JSON file
shaaha.import_profile("file")   # import a teammate's profile
shaaha.sync("http://team-server") # optional team server sync
"""
from __future__ import annotations
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger("shaaha.collab")


def share_profile(output_path: Optional[str] = None) -> str:
    """
    Export this machine's learned profile as a shareable JSON file.
    No sensitive data is included — only timing statistics.

    Args:
        output_path: where to save (default: ./shaaha_profile_export.json)

    Returns:
        Path to the exported file.
    """
    from shaaha.brain import Brain
    from shaaha.environment import Environment

    brain = Brain()
    env   = Environment.probe()

    export = {
        "shaaha_version": "2.0",
        "exported_at":    datetime.now().isoformat(),
        "machine_summary": {
            "python":     env.python_version,
            "os":         env.os_name,
            "cpu_cores":  env.cpu_cores,
            "cuda":       env.cuda_available,
        },
        "operations":  brain._data.get("operations", {}),
        "confidence":  brain.confidence(),
        "recommendations": brain.summary().get("recommendations", []),
    }

    out = Path(output_path or "shaaha_profile_export.json")
    out.write_text(json.dumps(export, indent=2), encoding="utf-8")
    print(f"✅ [Shaaha] Profile exported to: {out}")
    print(f"   Share this file with teammates — they can import it with:")
    print(f"   shaaha.import_profile('{out}')")
    return str(out)


def import_profile(filepath: str, merge: bool = True):
    """
    Import a teammate's profile to benefit from their learnings.

    Args:
        filepath: path to exported profile JSON
        merge:    True = merge with existing data, False = replace

    Example:
        shaaha.import_profile("alice_profile.json")
    """
    from shaaha.brain import Brain

    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"[Shaaha] Profile not found: {filepath}")

    imported = json.loads(path.read_text(encoding="utf-8"))
    brain    = Brain()

    their_ops = imported.get("operations", {})
    if not their_ops:
        print("[Shaaha] Imported profile has no operation data.")
        return

    if not merge:
        brain._data["operations"] = their_ops
    else:
        for key, entry in their_ops.items():
            if key not in brain._data.get("operations", {}):
                brain._data.setdefault("operations", {})[key] = entry
            else:
                # Merge timings (keep last 100)
                existing = brain._data["operations"][key]["timings"]
                incoming = entry.get("timings", [])
                merged   = (existing + incoming)[-100:]
                brain._data["operations"][key]["timings"] = merged
                brain._data["operations"][key]["count"] += entry.get("count", 0)

    brain._save()
    machine = imported.get("machine_summary", {})
    print(f"✅ [Shaaha] Profile imported from: {filepath}")
    print(f"   Source: Python {machine.get('python','?')} | "
          f"{machine.get('os','?')} | "
          f"CUDA={'yes' if machine.get('cuda') else 'no'}")
    print(f"   Operations merged: {len(their_ops)}")
    print(f"   Your new confidence: {brain.confidence()*100:.0f}%")


def sync(server_url: str, machine_id: Optional[str] = None):
    """
    Sync profile with a team server (optional, requires server setup).

    Args:
        server_url:  e.g. "http://your-team-server:8080"
        machine_id:  optional identifier for this machine

    Example:
        shaaha.sync("http://my-team-server:8080")
    """
    import socket, urllib.request, urllib.error

    from shaaha.brain import Brain
    brain = Brain()

    mid = machine_id or socket.gethostname()
    payload = json.dumps({
        "machine_id":  mid,
        "operations":  brain._data.get("operations", {}),
        "confidence":  brain.confidence(),
    }).encode()

    print(f"🔄 [Shaaha] Syncing with team server: {server_url}")
    try:
        req = urllib.request.Request(
            f"{server_url.rstrip('/')}/api/sync",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            print(f"✅ Sync complete. Team machines: {data.get('machines', '?')}")
            # Merge team data if returned
            if "operations" in data:
                for key, entry in data["operations"].items():
                    brain._data.setdefault("operations", {}).setdefault(key, entry)
                brain._save()
                print(f"   Merged {len(data['operations'])} team operations.")
    except urllib.error.URLError as e:
        print(f"❌ [Shaaha] Sync failed: {e}")
        print(f"   Make sure your team server is running at {server_url}")
        print(f"   Tip: Use shaaha.share_profile() for file-based sharing instead.")
