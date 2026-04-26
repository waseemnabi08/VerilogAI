import os
import re
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx
import json
import asyncio
from datetime import datetime

# ========= Config =========

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in .env file")

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# ========= Temperature per mode =========
# Lower = more deterministic/precise. Debug needs highest precision; explain can afford creativity.
TEMPERATURE = {
    "default": 0.10,
    "generate": 0.12,
    "debug": 0.05,   # Most critical — must be highly consistent
    "explain": 0.20,
    "testbench": 0.10,
    "optimize": 0.08,
}

# =========================================================================
# SYSTEM PROMPTS
# Design philosophy:
#   1. Role + persona  — who the model is
#   2. Hard rules      — non-negotiable constraints
#   3. Output format   — exact template the model must follow
#   4. Few-shot        — one worked example to lock in behaviour
# =========================================================================

SYSTEM_BASE = """\
You are VerilogAI — a senior RTL design engineer and verification expert with 15+ years of \
industry experience across ASIC tape-outs and FPGA products. You have deep knowledge of:
  • Digital design principles and synthesizable RTL coding
  • Synthesis tools: Synopsys DC, Cadence Genus, Xilinx Vivado, Intel Quartus
  • IEEE 1364-2001 (Verilog-2001) and IEEE 1800-2017 (SystemVerilog)
  • Timing closure, CDC, and low-power techniques
  • UVM-based verification methodology

Hard rules that always apply:
  • Never guess — if a spec is ambiguous, state your assumption explicitly.
  • Never produce non-synthesizable constructs in RTL code unless the user asks for simulation-only.
  • Always use non-blocking assignments (<=) in sequential (always_ff / always @posedge) blocks.
  • Always use blocking assignments (=) in combinational (always_comb / always @(*)) blocks.
  • Avoid latches: ensure every branch of a combinational block assigns every output.
  • Prefer parameters over magic numbers.
"""

# ----- GENERATE -----
SYSTEM_GENERATE = SYSTEM_BASE + """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MODE: RTL CODE GENERATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Additional generation rules:
  1. Use the language the user specifies (Verilog-2001 or SystemVerilog). Default: SystemVerilog.
  2. Always include: module header, parameter declarations, port list with directions & widths,
     inline signal comments, and a module instantiation template in a comment block at the end.
  3. Include an asynchronous active-low reset (rst_n) unless the user specifies otherwise.
  4. Add SVA assertions (// synthesis translate_off guards) where meaningful.
  5. Think through the design step-by-step before writing the module — identify edge cases first.

Output format — use EXACTLY this structure:
```
## Design Notes
[Brief explanation of the approach, assumptions made, and any trade-offs]

## RTL Code
```systemverilog
[complete module code]
```

## Instantiation Template
```systemverilog
[module_name] #(
    .PARAM (VALUE)
) u_[module_name] (
    .port (signal)
);
```

## Potential Issues / Next Steps
[Anything the user should watch out for during synthesis or simulation]
```

━━━ FEW-SHOT EXAMPLE ━━━
User: "Generate a parameterised synchronous FIFO in SystemVerilog. Depth and width should be configurable."

Response:
## Design Notes
A synchronous FIFO uses a single clock domain. I'll implement it with:
- A circular buffer (register array) indexed by read/write pointers.
- An extra pointer bit to distinguish full from empty (common industry trick — avoids a separate counter).
- Assumption: DEPTH must be a power of 2 for the pointer trick to work correctly. I'll add an assertion.

## RTL Code
```systemverilog
// sync_fifo.sv — Parameterised Synchronous FIFO
// Assumption: DEPTH must be a power of 2.
module sync_fifo #(
    parameter int unsigned DATA_WIDTH = 8,
    parameter int unsigned DEPTH      = 16   // Must be power of 2
) (
    input  logic                  clk,
    input  logic                  rst_n,
    // Write port
    input  logic                  wr_en,
    input  logic [DATA_WIDTH-1:0] wr_data,
    output logic                  full,
    // Read port
    input  logic                  rd_en,
    output logic [DATA_WIDTH-1:0] rd_data,
    output logic                  empty
);

    localparam int PTR_W = $clog2(DEPTH) + 1; // Extra bit distinguishes full/empty

    logic [DATA_WIDTH-1:0] mem [0:DEPTH-1];
    logic [PTR_W-1:0]      wr_ptr, rd_ptr;

    assign full  = (wr_ptr == {~rd_ptr[PTR_W-1], rd_ptr[PTR_W-2:0]});
    assign empty = (wr_ptr == rd_ptr);

    // Write logic
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr <= '0;
        end else if (wr_en && !full) begin
            mem[wr_ptr[PTR_W-2:0]] <= wr_data;
            wr_ptr <= wr_ptr + 1'b1;
        end
    end

    // Read logic
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rd_ptr  <= '0;
            rd_data <= '0;
        end else if (rd_en && !empty) begin
            rd_data <= mem[rd_ptr[PTR_W-2:0]];
            rd_ptr  <= rd_ptr + 1'b1;
        end
    end

    // Depth must be power of 2
    // synthesis translate_off
    initial begin
        assert ((DEPTH & (DEPTH - 1)) == 0)
            else $fatal(1, "sync_fifo: DEPTH must be a power of 2, got %0d", DEPTH);
    end
    // synthesis translate_on

endmodule
```

## Instantiation Template
```systemverilog
sync_fifo #(
    .DATA_WIDTH (8),
    .DEPTH      (16)
) u_sync_fifo (
    .clk     (clk),
    .rst_n   (rst_n),
    .wr_en   (wr_en),
    .wr_data (wr_data),
    .full    (full),
    .rd_en   (rd_en),
    .rd_data (rd_data),
    .empty   (empty)
);
```

## Potential Issues / Next Steps
- Simultaneous read+write when full/empty: currently dropped silently — add overflow/underflow flags if needed.
- If DEPTH is not a power of 2, the assertion fires at elaboration time.
- For FPGA targets, Vivado will infer this as distributed RAM for small depths and BRAM for large ones.
━━━ END OF EXAMPLE ━━━
"""

# ----- DEBUG -----
SYSTEM_DEBUG = SYSTEM_BASE + """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MODE: DEBUG & CODE REVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Think through the code step-by-step before writing your response.
Check each issue category in order:
  1. Syntax errors (will fail parsing)
  2. Latch inference (incomplete sensitivity list or missing else/default)
  3. Blocking/non-blocking assignment misuse
  4. Reset problems (missing reset, mixed sync/async)
  5. Width mismatches and implicit truncation
  6. Non-synthesizable constructs
  7. Race conditions and CDC violations
  8. Coding style / maintainability

Severity levels:
  🔴 CRITICAL — Will cause synthesis failure or functional incorrectness.
  🟡 WARNING  — May cause synthesis warnings or subtle bugs.
  🔵 INFO     — Style or readability improvement.

Output format — use EXACTLY this structure:
```
## Step-by-Step Analysis
[Walk through the code logically before listing issues]

## Issues Found

### 🔴 Critical
| # | Line | Issue | Fix |
|---|------|-------|-----|
| 1 | 42   | ...   | ... |

### 🟡 Warnings
| # | Line | Issue | Fix |
|---|------|-------|-----|

### 🔵 Info
| # | Line | Issue | Fix |
|---|------|-------|-----|

## Corrected Code
```verilog / ```systemverilog
[full corrected module]
```

## Summary
[2-3 sentence summary of the most important fixes]
```

━━━ FEW-SHOT EXAMPLE ━━━
User submits:
```verilog
module bad_counter(input clk, input en, output reg [3:0] count);
  always @(posedge clk) begin
    if (en)
      count = count + 1;
  end
endmodule
```

Response:
## Step-by-Step Analysis
The module is a simple counter. Walking through it:
- No reset → count has an undefined initial value in simulation and post-synthesis.
- Uses blocking assignment (=) inside a sequential always block → creates a race condition when multiple always blocks read `count` in the same time step.
- No else branch → but since count is a reg and only updated conditionally, synthesis infers a register (not a latch) here — acceptable, but missing reset is the real problem.

## Issues Found

### 🔴 Critical
| # | Line | Issue | Fix |
|---|------|-------|-----|
| 1 | 1    | No reset signal — count is X at power-on | Add `rst_n` port and reset logic |
| 2 | 4    | Blocking `=` in sequential block — race condition | Change to `<=` |

### 🟡 Warnings
| # | Line | Issue | Fix |
|---|------|-------|-----|
| 1 | 2    | Verilog-2001 `always @(posedge clk)` — consider `always_ff` (SystemVerilog) | Use `always_ff` if targeting SV |

### 🔵 Info
| # | Line | Issue | Fix |
|---|------|-------|-----|
| 1 | 1    | Magic number `4` for width — use a parameter | `parameter int WIDTH = 4` |

## Corrected Code
```verilog
module bad_counter #(
    parameter integer WIDTH = 4
) (
    input  wire             clk,
    input  wire             rst_n,   // Active-low async reset
    input  wire             en,
    output reg  [WIDTH-1:0] count
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= {WIDTH{1'b0}};
        else if (en)
            count <= count + 1'b1;
    end
endmodule
```

## Summary
Two critical bugs: missing reset (undefined post-synthesis behaviour) and blocking assignment in a sequential block (race condition). Fixed both, added a width parameter for reusability.
━━━ END OF EXAMPLE ━━━
"""

# ----- EXPLAIN -----
SYSTEM_EXPLAIN = SYSTEM_BASE + """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MODE: CODE EXPLANATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Your goal is deep, clear explanation — not code modification.
Calibrate depth to the user's stated level (beginner / intermediate / advanced).
Use analogies where they genuinely help (don't force them).

Output format — use EXACTLY this structure:
```
## What This Module Does
[1–2 sentence plain-English summary]

## Port Table
| Port | Direction | Width | Purpose |
|------|-----------|-------|---------|

## How It Works — Step by Step
[Walk through the logic in execution order, not code order]

## Timing & Clocking
[Clock domains, reset strategy, any CDC concerns]

## Key Design Decisions
[Why the author likely made specific choices — trade-offs]

## Common Pitfalls
[What could go wrong if someone modifies or instantiates this incorrectly]

## Learning Points
[2–3 bullet takeaways for a student]
```
"""

# ----- TESTBENCH -----
SYSTEM_TESTBENCH = SYSTEM_BASE + """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MODE: TESTBENCH GENERATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generate a self-checking testbench. Think through the DUT's interface and
corner cases before writing the TB.

Rules:
  1. Generate a proper clock (typically 10ns period unless specified).
  2. Apply reset at the start and release cleanly after a few cycles.
  3. Cover: normal operation, corner cases, error/overflow conditions.
  4. Use $display/$error/$fatal for pass/fail reporting — no relying on waveform inspection alone.
  5. End simulation with $finish and a test summary.
  6. Use SystemVerilog unless the user asks for Verilog-2001.

Output format:
```
## Test Plan
[Bullet list of scenarios being tested and why]

## Testbench Code
```systemverilog
[complete testbench]
```

## How to Run
[Tool-agnostic simulation command, e.g. for ModelSim / VCS / Verilator]
```
"""

# ----- OPTIMIZE -----
SYSTEM_OPTIMIZE = SYSTEM_BASE + """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MODE: RTL OPTIMISATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Analyse the code for area, timing, and power, then produce an optimised version.
Always explain the trade-off of every change — never optimise silently.

Output format:
```
## Current Design Assessment
| Metric      | Estimate | Notes |
|-------------|----------|-------|
| Logic depth | N gates  | ...   |
| Key concern | ...      | ...   |

## Optimisation Opportunities
[Ranked by impact]

## Optimised Code
```systemverilog
[code]
```

## Trade-off Summary
[What was gained and what (if anything) was sacrificed]
```
"""

# =========================================================================
# FastAPI app
# =========================================================================

app = FastAPI(
    title="VerilogAI — Enhanced Backend",
    description="Advanced Verilog/SystemVerilog design assistant",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================================
# Request models
# =========================================================================

class ChatRequest(BaseModel):
    prompt: str
    history: Optional[List[Dict[str, str]]] = None
    context: Optional[str] = None

class GenerateRequest(BaseModel):
    spec: str
    history: Optional[List[Dict[str, str]]] = None
    language: str = Field(default="systemverilog")
    target: str = Field(default="generic", description="fpga | asic | generic")
    optimization: str = Field(default="balanced", description="area | speed | power | balanced")
    include_assertions: bool = Field(default=True)
    include_coverage: bool = Field(default=False)

class CodeRequest(BaseModel):
    code: str
    history: Optional[List[Dict[str, str]]] = None
    file_name: Optional[str] = None
    analysis_depth: str = Field(default="standard", description="basic | standard | comprehensive")

class OptimizeRequest(BaseModel):
    code: str
    history: Optional[List[Dict[str, str]]] = None
    target: str = Field(default="fpga")
    objective: str = Field(default="balanced")
    constraints: Optional[Dict[str, Any]] = None

class TestbenchRequest(BaseModel):
    dut_code: str
    history: Optional[List[Dict[str, str]]] = None
    test_type: str = Field(default="comprehensive")
    language: str = Field(default="systemverilog")
    include_coverage: bool = Field(default=True)

# =========================================================================
# Static analyser (unchanged from original — good utility)
# =========================================================================

class VerilogAnalyzer:
    @staticmethod
    def extract_modules(code: str) -> List[Dict[str, str]]:
        modules = []
        pattern = r'module\s+(\w+)\s*(?:#\([^)]*\))?\s*\(([^;]*)\);'
        for m in re.finditer(pattern, code, re.MULTILINE | re.DOTALL):
            modules.append({
                'name': m.group(1),
                'ports': m.group(2).strip(),
            })
        return modules

    @staticmethod
    def analyze_clock_domains(code: str) -> List[str]:
        clocks = set()
        for pat in [
            r'always_ff\s*@\s*\(\s*posedge\s+(\w+)',
            r'always\s*@\s*\(\s*posedge\s+(\w+)',
            r'always_ff\s*@\s*\(\s*negedge\s+(\w+)',
        ]:
            clocks.update(re.findall(pat, code))
        return list(clocks)

    @staticmethod
    def check_coding_style(code: str) -> List[Dict[str, str]]:
        issues = []
        for i, line in enumerate(code.split('\n'), 1):
            if ('always_ff' in line or 'always @(posedge' in line):
                if '=' in line and '<=' not in line and '//' not in line.split('=')[0]:
                    issues.append({'type': 'warning', 'line': i,
                                   'message': 'Blocking assignment in sequential block'})
            if re.search(r'\b\d{2,}\b', line) and 'parameter' not in line and '//' not in line:
                issues.append({'type': 'info', 'line': i,
                               'message': 'Magic number — consider a parameter'})
        return issues

# =========================================================================
# Gemini API helper
# =========================================================================

def _build_contents(system_prompt: str,
                    history: Optional[List[Dict[str, str]]],
                    user_msg: str) -> List[Dict]:
    """
    Build the Gemini `contents` list.
    Gemini doesn't have a first-class system role in the REST API, so we
    prepend the system prompt as the first user turn and a short model ack,
    then replay the conversation history, then append the new user message.
    """
    contents = [
        {"role": "user",  "parts": [{"text": system_prompt}]},
        {"role": "model", "parts": [{"text": "Understood. I'm ready to help."}]},
    ]
    if history:
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    contents.append({"role": "user", "parts": [{"text": user_msg}]})
    return contents


async def call_gemini(system_prompt: str,
                      user_msg: str,
                      history: Optional[List[Dict[str, str]]] = None,
                      mode: str = "default",
                      max_retries: int = 3) -> str:
    contents = _build_contents(system_prompt, history, user_msg)
    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": TEMPERATURE.get(mode, TEMPERATURE["default"]),
            "maxOutputTokens": 8192,
            "topP": 0.8,
            "topK": 40,
        },
    }
    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(payload),
                )
            if resp.status_code == 200:
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            if resp.status_code == 429 and attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        except HTTPException:
            raise
        except Exception as e:
            if attempt == max_retries - 1:
                raise HTTPException(status_code=500, detail=str(e))
            await asyncio.sleep(1)

# =========================================================================
# Routes
# =========================================================================

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "2.1.0",
        "modes": ["chat", "generate", "debug", "explain", "optimize", "testbench", "analyze"],
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    """General-purpose Verilog/HDL chat with conversation history."""
    try:
        extra = f"\nAdditional context: {req.context}" if req.context else ""
        reply = await call_gemini(
            system_prompt=SYSTEM_BASE + extra,
            user_msg=req.prompt,
            history=req.history,
            mode="default",
        )
        return {"reply": reply, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate")
async def generate(req: GenerateRequest):
    """Generate synthesisable RTL from a natural-language spec."""
    try:
        opt_map = {
            "area":     "Prioritise resource sharing and logic minimisation.",
            "speed":    "Focus on reducing critical-path delay and maximising Fmax.",
            "power":    "Use clock gating and minimise switching activity.",
            "balanced": "Balance area, timing, and power.",
        }
        tgt_map = {
            "fpga":    "Optimise for FPGA primitives (LUTs, FFs, BRAMs, DSPs).",
            "asic":    "Target standard-cell libraries; avoid FPGA-specific constructs.",
            "generic": "Write portable, tool-agnostic synthesisable code.",
        }

        user_msg = f"""\
Generate a {req.language} RTL module from the specification below.

Constraints:
  - Target platform : {req.target} — {tgt_map.get(req.target, '')}
  - Optimisation    : {req.optimization} — {opt_map.get(req.optimization, '')}
  - Assertions      : {'Include SVA assertions' if req.include_assertions else 'Skip assertions'}
  - Coverage        : {'Include covergroups' if req.include_coverage else 'Skip coverage'}

Think step-by-step: identify the state elements, the combinational logic, \
and any edge cases before writing the module.

Specification:
{req.spec}
"""
        reply = await call_gemini(
            system_prompt=SYSTEM_GENERATE,
            user_msg=user_msg,
            history=req.history,
            mode="generate",
        )
        return {
            "reply": reply,
            "metadata": {"language": req.language, "target": req.target},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debug")
async def debug(req: CodeRequest):
    """Debug, review, and correct Verilog/SystemVerilog code."""
    try:
        analyzer = VerilogAnalyzer()
        modules = analyzer.extract_modules(req.code)
        clocks  = analyzer.analyze_clock_domains(req.code)
        style   = analyzer.check_coding_style(req.code)

        # Feed static-analysis context into the prompt so the model
        # doesn't waste tokens re-discovering what we already know.
        static_ctx = (
            f"Static pre-analysis (use as hints, not gospel):\n"
            f"  Modules  : {[m['name'] for m in modules] or 'none detected'}\n"
            f"  Clocks   : {clocks or 'none detected'}\n"
            f"  Style hits: {len(style)} (blocking-in-seq, magic numbers)\n"
        )

        user_msg = f"""\
Review and debug the Verilog/SystemVerilog code below.
Analysis depth requested: {req.analysis_depth}

{static_ctx}

Think step-by-step through each issue category before writing the issue table.
Then produce the corrected code.

Code:
{req.code}
"""
        reply = await call_gemini(
            system_prompt=SYSTEM_DEBUG,
            user_msg=user_msg,
            history=req.history,
            mode="debug",
        )
        return {
            "reply": reply,
            "static_analysis": {
                "modules": modules,
                "clock_domains": clocks,
                "style_issues": style,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/explain")
async def explain(req: CodeRequest):
    """Explain Verilog/SystemVerilog code at the requested depth."""
    try:
        loc = len([l for l in req.code.split('\n') if l.strip()])
        complexity = "high" if loc > 100 else "medium" if loc > 50 else "low"

        analyzer = VerilogAnalyzer()
        modules  = analyzer.extract_modules(req.code)
        clocks   = analyzer.analyze_clock_domains(req.code)

        user_msg = f"""\
Explain the following Verilog/SystemVerilog code.

Context for your explanation:
  - Requested depth : {req.analysis_depth}
  - Code complexity : {complexity} ({loc} non-blank lines)
  - Modules         : {[m['name'] for m in modules] or 'see code'}
  - Clock domains   : {clocks or 'not yet identified'}

Use the output format from your instructions exactly.

Code:
{req.code}
"""
        reply = await call_gemini(
            system_prompt=SYSTEM_EXPLAIN,
            user_msg=user_msg,
            history=req.history,
            mode="explain",
        )
        return {
            "reply": reply,
            "context": {"modules": len(modules), "complexity": complexity},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/testbench")
async def generate_testbench(req: TestbenchRequest):
    """Generate a self-checking testbench for the provided DUT."""
    try:
        analyzer = VerilogAnalyzer()
        modules  = analyzer.extract_modules(req.dut_code)
        if not modules:
            raise HTTPException(status_code=400, detail="No module found in DUT code.")

        user_msg = f"""\
Generate a {req.language} testbench for the DUT below.

Requirements:
  - Test type       : {req.test_type}
  - Coverage        : {'Include covergroups and cover properties' if req.include_coverage else 'Skip formal coverage'}
  - DUT modules     : {[m['name'] for m in modules]}

Think through the DUT's behaviour first, then plan the test scenarios \
before writing any code.

DUT Code:
{req.dut_code}
"""
        reply = await call_gemini(
            system_prompt=SYSTEM_TESTBENCH,
            user_msg=user_msg,
            history=req.history,
            mode="testbench",
        )
        return {"reply": reply, "dut_modules": [m['name'] for m in modules]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/optimize")
async def optimize(req: OptimizeRequest):
    """Optimise RTL for area, timing, or power."""
    try:
        constraints_text = (
            f"\nUser-provided constraints:\n{json.dumps(req.constraints, indent=2)}"
            if req.constraints else ""
        )

        user_msg = f"""\
Optimise the Verilog code below for {req.target} implementation.

Objective: {req.objective}
{constraints_text}

Think through the current design's bottlenecks first, then propose changes \
in order of impact.

Code:
{req.code}
"""
        reply = await call_gemini(
            system_prompt=SYSTEM_OPTIMIZE,
            user_msg=user_msg,
            history=req.history,
            mode="optimize",
        )
        return {"reply": reply, "optimization_target": req.objective}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze")
async def analyze_code(req: CodeRequest):
    """Comprehensive static + AI analysis without modifying the code."""
    try:
        analyzer = VerilogAnalyzer()
        modules  = analyzer.extract_modules(req.code)
        clocks   = analyzer.analyze_clock_domains(req.code)
        style    = analyzer.check_coding_style(req.code)
        loc      = len([l for l in req.code.split('\n') if l.strip()])

        user_msg = f"""\
Provide a comprehensive analysis of the Verilog code below. Do NOT modify the code.

Pre-computed metrics:
  - Modules         : {len(modules)} ({[m['name'] for m in modules]})
  - Clock domains   : {len(clocks)} ({clocks})
  - Lines of code   : {loc}
  - Style issues    : {len(style)}

Cover:
  1. Design complexity and maintainability
  2. Synthesis implications and resource usage estimates
  3. Timing and CDC considerations
  4. Power implications
  5. Verification challenges
  6. Compliance with industry best practices
  7. Portability across synthesis tools

Code:
{req.code}
"""
        reply = await call_gemini(
            system_prompt=SYSTEM_BASE + "\nDo NOT produce modified code. Analysis only.",
            user_msg=user_msg,
            history=req.history,
            mode="debug",
        )
        return {
            "reply": reply,
            "metrics": {
                "modules": len(modules),
                "clock_domains": len(clocks),
                "lines_of_code": loc,
                "style_issues": len(style),
            },
            "details": {
                "modules": modules,
                "clock_domains": clocks,
                "style_issues": style,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a Verilog/SystemVerilog file for analysis."""
    try:
        if not file.filename.endswith(('.v', '.sv', '.vh', '.svh')):
            raise HTTPException(
                status_code=400,
                detail="Only Verilog files (.v, .sv, .vh, .svh) are supported."
            )
        content = await file.read()
        code    = content.decode('utf-8')
        modules = VerilogAnalyzer().extract_modules(code)
        return {
            "filename": file.filename,
            "size": len(content),
            "modules": [m['name'] for m in modules],
            "preview": code[:500] + "..." if len(code) > 500 else code,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
