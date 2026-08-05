"""
shaaha.agent — Layer 2: The AI Agent
======================================
Natural language task execution engine.

shaaha.agent("analyse sales.csv and find anomalies then plot them")

The agent:
1. Sends the task to Claude API
2. Gets back a step-by-step execution plan as JSON
3. Executes each step using the correct shaaha domain
4. Shows real-time progress
5. Saves a markdown report

SECURITY: _execute_step() runs the plan's "code" fields through exec()
with the calling process's full privileges - whether that plan came from
the Claude API or the offline fallback planner. Never call agent()/run()
with untrusted task strings or in a multi-tenant process.
"""
from __future__ import annotations

import json
import time
import logging
import traceback
from pathlib import Path
from typing import Optional

logger = logging.getLogger("shaaha.agent")

_AGENT_SYSTEM_PROMPT = """
You are the Shaaha AI Agent. Shaaha is a Python meta-dispatcher library.

Given a natural language task from a data scientist, you must produce a JSON execution plan.

Available shaaha domains:
- shaaha.dataframe  → polars/pandas  (read_csv, DataFrame, groupby, merge, etc.)
- shaaha.math       → numpy/cupy     (array, sqrt, mean, std, etc.)  
- shaaha.ml         → sklearn/torch  (LinearRegression, RandomForestClassifier, train_test_split, etc.)
- shaaha.stats      → scipy/statsmodels (describe, normaltest, pearsonr, etc.)
- shaaha.image      → cv2/pillow     (open, resize, to_grayscale, etc.)
- shaaha.viz        → plotly/matplotlib (Figure, show, plot, scatter, bar, etc.)
- shaaha.nlp        → transformers/spacy (pipeline, tokenize, etc.)
- shaaha.http       → httpx/requests (get, post, etc.)

Each step's domain proxy is available in your code as `shaaha_<domain>`,
e.g. the "dataframe" domain is `shaaha_dataframe`, "math" is `shaaha_math`.

Respond ONLY with valid JSON in this exact format:
{
  "task_summary": "one sentence description of what you will do",
  "steps": [
    {
      "step_number": 1,
      "description": "Load the CSV file",
      "domain": "dataframe",
      "action": "read_csv",
      "code": "data = shaaha_dataframe.read_csv('{file_path}')",
      "output_var": "data"
    }
  ],
  "report_title": "Analysis Report",
  "estimated_time": "~30 seconds"
}

Rules:
- Use real Python code in the "code" field
- Reference previous step outputs by their output_var names
- For visualization steps, save figures to disk: fig.savefig('shaaha_report.png') or fig.write_html('shaaha_report.html')
- Keep steps atomic and clear
- Maximum 10 steps
- output_var must be a valid Python identifier
"""


class ShaahAgent:
    """The AI Agent — turns natural language into executed Python workflows."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._context: dict = {}   # holds output variables between steps
        self._log: list[dict] = []

    def run(self, task: str, save_report: bool = True) -> dict:
        """
        Execute a natural language task end-to-end.

        Args:
            task:        e.g. "analyse sales.csv and find anomalies then plot them"
            save_report: write a markdown report to ./shaaha_report.md

        Returns:
            dict with keys: success, steps_completed, results, report_path
        """
        print(f"\n🧠 [Shaaha Agent] Task received: \"{task}\"")
        print("   Planning execution steps...\n")

        # Step 1 — Get execution plan from LLM
        plan = self._plan(task)
        if plan is None:
            return {"success": False, "error": "Could not generate execution plan."}

        print(f"📋 Plan: {plan.get('task_summary', task)}")
        print(f"   Steps: {len(plan['steps'])} | Est. time: {plan.get('estimated_time','?')}\n")

        # Step 2 — Execute each step
        results = []
        for step in plan["steps"]:
            result = self._execute_step(step)
            results.append(result)
            if not result["success"]:
                print(f"   ❌ Step {step['step_number']} failed — stopping.\n")
                break

        success = all(r["success"] for r in results)

        # Step 3 — Save report
        report_path = None
        if save_report:
            report_path = self._save_report(task, plan, results)

        print(f"\n{'✅' if success else '❌'} Agent finished. "
              f"{sum(r['success'] for r in results)}/{len(results)} steps completed.")
        if report_path:
            print(f"📄 Report saved: {report_path}\n")

        return {
            "success": success,
            "steps_completed": sum(r["success"] for r in results),
            "total_steps": len(results),
            "results": results,
            "report_path": report_path,
            "context": self._context,
        }

    def _plan(self, task: str) -> Optional[dict]:
        """Call Claude API to get a JSON execution plan."""
        import os
        from shaaha._llm import call_claude, strip_json_fence

        api_key = self.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            print("⚠️  No ANTHROPIC_API_KEY found. Using fallback planner.")
            return self._fallback_plan(task)

        try:
            text = call_claude(
                task, api_key, system=_AGENT_SYSTEM_PROMPT,
                max_tokens=2000, timeout=30,
            )
            return json.loads(strip_json_fence(text))

        except Exception as e:
            logger.warning("Agent LLM call failed: %s", e)
            print(f"⚠️  LLM unavailable ({e}). Using fallback planner.")
            return self._fallback_plan(task)

    def _fallback_plan(self, task: str) -> dict:
        """Rule-based planner when LLM is not available."""
        task_lower = task.lower()
        steps = []
        n = 1

        # Detect file reference
        import re
        files = re.findall(r'[\w/\\.-]+\.(?:csv|xlsx|json|parquet)', task)

        if files:
            steps.append({
                "step_number": n, "description": f"Load {files[0]}",
                "domain": "dataframe", "action": "read_csv",
                "code": f"data = shaaha_dataframe.read_csv('{files[0]}')",
                "output_var": "data"
            })
            n += 1

        if any(w in task_lower for w in ["anomal", "outlier", "unusual"]):
            steps.append({
                "step_number": n, "description": "Compute statistics to find anomalies",
                "domain": "math", "action": "std",
                "code": ("numeric_cols = data.select_dtypes(include='number') if hasattr(data, 'select_dtypes') else data\n"
                         "stats = {'mean': float(numeric_cols.values.mean()), 'std': float(numeric_cols.values.std())}"),
                "output_var": "stats"
            })
            n += 1

        if any(w in task_lower for w in ["plot", "chart", "visual", "graph"]):
            steps.append({
                "step_number": n, "description": "Create visualization",
                "domain": "viz", "action": "plot",
                "code": ("import matplotlib\nmatplotlib.use('Agg')\nimport matplotlib.pyplot as plt\n"
                         "fig, ax = plt.subplots(figsize=(10, 6))\n"
                         "if 'data' in dir():\n"
                         "    numeric = data.select_dtypes(include='number') if hasattr(data,'select_dtypes') else data\n"
                         "    numeric.iloc[:, 0].plot(ax=ax, title='Shaaha Analysis')\n"
                         "plt.tight_layout()\nplt.savefig('shaaha_report.png', dpi=150)\nprint('Chart saved: shaaha_report.png')"),
                "output_var": "fig"
            })
            n += 1

        if not steps:
            steps.append({
                "step_number": 1, "description": "Display task summary",
                "domain": "math", "action": "info",
                "code": f"print('Task: {task}')",
                "output_var": "result"
            })

        return {
            "task_summary": f"Fallback plan for: {task}",
            "steps": steps,
            "report_title": "Shaaha Analysis Report",
            "estimated_time": "~10 seconds",
        }

    def _execute_step(self, step: dict) -> dict:
        """Execute one plan step inside a shared context namespace."""
        num   = step["step_number"]
        desc  = step["description"]
        code  = step["code"]
        domain = step.get("domain", "")

        print(f"  ▶  Step {num}: {desc}")
        start = time.perf_counter()

        try:
            # Inject shaaha domain proxies into execution namespace
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            import shaaha

            exec_globals = {
                "__builtins__": __builtins__,
                "shaaha": shaaha,
                "print": print,
            }

            # Pre-import relevant domain
            if domain:
                try:
                    dom_mod = __import__(f"shaaha.{domain}", fromlist=[domain])
                    exec_globals[f"shaaha_{domain.replace('.','_')}"] = dom_mod
                    exec_globals[domain] = dom_mod
                except Exception:
                    pass

            # Inject previous step outputs
            exec_globals.update(self._context)

            # SECURITY: runs with this process's full privileges - see the
            # module docstring. `code` comes from the LLM plan or the
            # offline fallback planner, never from raw user input directly.
            exec(code, exec_globals)   # noqa: S102

            # Capture output variables
            elapsed = (time.perf_counter() - start) * 1000
            output_var = step.get("output_var")
            if output_var and output_var in exec_globals:
                self._context[output_var] = exec_globals[output_var]

            print(f"     ✓ Done ({elapsed:.0f}ms)")
            return {"step": num, "success": True, "elapsed_ms": elapsed,
                    "description": desc, "output_var": output_var}

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            err = traceback.format_exc()
            print(f"     ✗ Error: {e}")
            logger.error("Step %d failed: %s", num, err)
            return {"step": num, "success": False, "elapsed_ms": elapsed,
                    "description": desc, "error": str(e)}

    def _save_report(self, task: str, plan: dict, results: list) -> str:
        """Write a markdown execution report."""
        from datetime import datetime
        lines = [
            f"# {plan.get('report_title', 'Shaaha Agent Report')}",
            f"\n**Task:** {task}",
            f"\n**Summary:** {plan.get('task_summary', '')}",
            f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n**Status:** {'✅ Success' if all(r['success'] for r in results) else '❌ Partial failure'}",
            "\n---\n## Execution Steps\n",
        ]
        for r in results:
            icon = "✅" if r["success"] else "❌"
            lines.append(f"### {icon} Step {r['step']}: {r['description']}")
            lines.append(f"- Time: {r['elapsed_ms']:.0f}ms")
            if "error" in r:
                lines.append(f"- Error: `{r['error']}`")
            lines.append("")

        path = Path("shaaha_report.md")
        path.write_text("\n".join(lines), encoding="utf-8")
        return str(path)


def agent(task: str, api_key: Optional[str] = None, save_report: bool = True) -> dict:
    """
    Public API — run a natural language task with the Shaaha Agent.

    Security: this executes generated Python via exec() with the calling
    process's full privileges. Only use with trusted task strings.

    Example:
        import shaaha
        shaaha.agent("load sales.csv and plot the top 5 categories")
    """
    ag = ShaahAgent(api_key=api_key)
    return ag.run(task, save_report=save_report)
