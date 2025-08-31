# main.py
import os
import re
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional, Tuple
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

# ========= Enhanced System Prompts =========
SYSTEM_BASE = (
    "You are VerilogAI — an expert assistant for hardware design, Verilog/SystemVerilog, "
    "FPGA development, and testbench generation. You have deep knowledge of:\n"
    "- Digital design principles and RTL coding\n"
    "- Synthesis tools (Synopsys, Cadence, Vivado, Quartus)\n"
    "- Industry-standard coding guidelines (SNUG, IEEE 1800)\n"
    "- Timing analysis and optimization\n"
    "- FPGA architectures (Xilinx, Intel/Altera)\n"
    "Be precise, follow synthesizable best practices, and consider real-world design constraints."
)

SYSTEM_GENERATE = (
    SYSTEM_BASE +
    "\nVerilog Generation Rules:\n"
    "1. Target SystemVerilog or Verilog-2001 based on user preference\n"
    "2. Use proper coding style: non-blocking (<=) for sequential, blocking (=) for combinational\n"
    "3. Always include proper reset logic (async reset preferred)\n"
    "4. Avoid latches: use complete sensitivity lists or always_comb/always_ff\n"
    "5. Include parameter declarations for configurability\n"
    "6. Add comprehensive port comments and signal descriptions\n"
    "7. Consider timing constraints and critical paths\n"
    "8. Include assertions where appropriate for verification\n"
    "9. Follow naming conventions (lowercase with underscores)\n"
    "10. Provide module instantiation template in comments\n"
)

SYSTEM_DEBUG = (
    SYSTEM_BASE +
    "\nDebug Analysis Framework:\n"
    "1. Syntax errors and typos\n"
    "2. Latch inference issues\n"
    "3. Reset and clock domain problems\n"
    "4. Non-synthesizable constructs\n"
    "5. Timing violations and race conditions\n"
    "6. Coding style violations\n"
    "7. Potential synthesis warnings\n"
    "8. Power optimization opportunities\n"
    "Return: Issue severity (Critical/Warning/Info), description, line number (if applicable), and corrected code."
)

SYSTEM_TESTBENCH = (
    SYSTEM_BASE +
    "\nTestbench Generation Rules:\n"
    "1. Use SystemVerilog features: classes, randomization, interfaces\n"
    "2. Include comprehensive test scenarios: corner cases, error conditions\n"
    "3. Implement proper clock and reset generation\n"
    "4. Add coverage collection (functional and code coverage)\n"
    "5. Use assertions for protocol checking\n"
    "6. Include self-checking mechanisms with pass/fail reporting\n"
    "7. Generate both directed and constrained-random tests\n"
    "8. Add timing checks and performance metrics\n"
)

SYSTEM_OPTIMIZE = (
    SYSTEM_BASE +
    "\nOptimization Analysis:\n"
    "1. Area optimization: resource sharing, logic minimization\n"
    "2. Timing optimization: pipelining, parallelization, critical path analysis\n"
    "3. Power optimization: clock gating, power islands\n"
    "4. Memory optimization: RAM/ROM inference, BRAM usage\n"
    "5. FPGA-specific optimizations: DSP blocks, carry chains\n"
    "Provide before/after comparisons and implementation trade-offs."
)

# ========= FastAPI app =========
app = FastAPI(
    title="VerilogAI - Enhanced Backend",
    description="Advanced Verilog/SystemVerilog design assistant with comprehensive analysis capabilities",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:3000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========= Enhanced Request Models =========
class ChatRequest(BaseModel):
    prompt: str
    history: Optional[List[Dict[str, str]]] = None
    context: Optional[str] = None  # Additional context for specialized queries

class GenerateRequest(BaseModel):
    spec: str
    language: str = Field(default="systemverilog", description="verilog2001 or systemverilog")
    target: str = Field(default="generic", description="fpga, asic, or generic")
    optimization: str = Field(default="balanced", description="area, speed, power, or balanced")
    include_assertions: bool = Field(default=True)
    include_coverage: bool = Field(default=False)

class CodeRequest(BaseModel):
    code: str
    file_name: Optional[str] = None
    analysis_depth: str = Field(default="standard", description="basic, standard, or comprehensive")

class OptimizeRequest(BaseModel):
    code: str
    target: str = Field(default="fpga", description="fpga or asic")
    objective: str = Field(default="balanced", description="area, timing, power, or balanced")
    constraints: Optional[Dict[str, Any]] = None

class TestbenchRequest(BaseModel):
    dut_code: str
    test_type: str = Field(default="comprehensive", description="basic, comprehensive, or performance")
    language: str = Field(default="systemverilog")
    include_coverage: bool = Field(default=True)

# ========= Enhanced Verilog Analysis Functions =========
class VerilogAnalyzer:
    @staticmethod
    def extract_modules(code: str) -> List[Dict[str, str]]:
        """Extract module information from Verilog code"""
        modules = []
        module_pattern = r'module\s+(\w+)\s*(?:#\([^)]*\))?\s*\(([^;]*)\);'
        matches = re.finditer(module_pattern, code, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            modules.append({
                'name': match.group(1),
                'ports': match.group(2).strip(),
                'start_pos': match.start(),
                'end_pos': match.end()
            })
        return modules

    @staticmethod
    def analyze_clock_domains(code: str) -> List[str]:
        """Identify clock domains in the code"""
        clock_signals = set()
        # Look for common clock patterns
        patterns = [
            r'always_ff\s*@\s*\(\s*posedge\s+(\w+)',
            r'always\s*@\s*\(\s*posedge\s+(\w+)',
            r'always_ff\s*@\s*\(\s*negedge\s+(\w+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, code)
            clock_signals.update(matches)
        
        return list(clock_signals)

    @staticmethod
    def check_coding_style(code: str) -> List[Dict[str, str]]:
        """Check for coding style violations"""
        issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for blocking assignments in sequential blocks
            if 'always_ff' in line or 'always @(posedge' in line:
                if '=' in line and '<=' not in line and '//' not in line.split('=')[0]:
                    issues.append({
                        'type': 'warning',
                        'line': i,
                        'message': 'Consider using non-blocking assignment (<=) in sequential logic'
                    })
            
            # Check for magic numbers
            if re.search(r'\b\d{2,}\b', line) and 'parameter' not in line and '//' not in line:
                issues.append({
                    'type': 'info',
                    'line': i,
                    'message': 'Consider using parameters for numeric constants'
                })
        
        return issues

# ========= Enhanced Gemini API Helper =========
async def call_gemini_with_retry(messages: List[Dict[str, str]], max_retries: int = 3) -> str:
    """Enhanced Gemini API call with retry logic and better error handling"""
    for attempt in range(max_retries):
        try:
            contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })
            
            payload = {
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.1,  # Lower temperature for more consistent technical responses
                    "maxOutputTokens": 8192,
                    "topP": 0.8,
                    "topK": 40
                }
            }
            
            url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, headers=headers, data=json.dumps(payload))
            
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            elif resp.status_code == 429:  # Rate limit
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
            
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
            
        except Exception as e:
            if attempt == max_retries - 1:
                raise HTTPException(status_code=500, detail=f"API call failed after {max_retries} attempts: {str(e)}")
            await asyncio.sleep(1)

# ========= Enhanced Routes =========
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "features": ["generate", "debug", "explain", "optimize", "testbench", "analyze"]
    }

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        messages = [{"role": "system", "content": SYSTEM_BASE}]
        
        if req.context:
            messages.append({"role": "system", "content": f"Additional context: {req.context}"})
        
        if req.history:
            messages.extend(req.history)
        
        messages.append({"role": "user", "content": req.prompt})
        
        reply = await call_gemini_with_retry(messages=messages)
        return {"reply": reply, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate")
async def generate(req: GenerateRequest):
    try:
        optimization_guidance = {
            "area": "Prioritize resource sharing and logic minimization",
            "speed": "Focus on reducing critical path delay and maximizing clock frequency",
            "power": "Implement clock gating and minimize switching activity",
            "balanced": "Balance area, timing, and power considerations"
        }
        
        target_guidance = {
            "fpga": "Optimize for FPGA resources (LUTs, FFs, BRAMs, DSPs)",
            "asic": "Consider standard cell libraries and manufacturing constraints",
            "generic": "Write portable, synthesis-friendly code"
        }
        
        user_msg = f"""Generate a {req.language} module from this specification.

Requirements:
- Target: {req.target} ({target_guidance[req.target]})
- Optimization: {req.optimization} ({optimization_guidance[req.optimization]})
- Include assertions: {req.include_assertions}
- Include coverage: {req.include_coverage}

Additional guidelines:
- Use proper reset methodology
- Include comprehensive comments
- Add parameter documentation
- Provide instantiation template
- Consider testability (DFT)

Specification:
{req.spec}"""

        reply = await call_gemini_with_retry(
            messages=[
                {"role": "system", "content": SYSTEM_GENERATE},
                {"role": "user", "content": user_msg},
            ]
        )
        return {"reply": reply, "metadata": {"language": req.language, "target": req.target}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/debug")
async def debug(req: CodeRequest):
    try:
        # Perform static analysis
        analyzer = VerilogAnalyzer()
        modules = analyzer.extract_modules(req.code)
        clocks = analyzer.analyze_clock_domains(req.code)
        style_issues = analyzer.check_coding_style(req.code)
        
        analysis_context = f"""
Static Analysis Results:
- Modules found: {[m['name'] for m in modules]}
- Clock domains: {clocks}
- Style issues: {len(style_issues)} found
"""
        
        user_msg = f"""Analyze and debug the following {req.language if hasattr(req, 'language') else 'Verilog'} code.
Analysis depth: {req.analysis_depth}

{analysis_context}

Provide:
1. Critical issues (synthesis blockers)
2. Warnings (potential problems)  
3. Style improvements
4. Corrected code with explanations

Code:
{req.code}"""

        reply = await call_gemini_with_retry(
            messages=[
                {"role": "system", "content": SYSTEM_DEBUG},
                {"role": "user", "content": user_msg},
            ]
        )
        
        return {
            "reply": reply,
            "static_analysis": {
                "modules": modules,
                "clock_domains": clocks,
                "style_issues": style_issues
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/optimize")
async def optimize(req: OptimizeRequest):
    try:
        constraints_text = ""
        if req.constraints:
            constraints_text = f"Constraints: {json.dumps(req.constraints, indent=2)}"
        
        user_msg = f"""Optimize the following Verilog code for {req.target} implementation.
Objective: {req.objective}
{constraints_text}

Provide:
1. Current design analysis (area, timing, power estimates)
2. Optimization opportunities
3. Optimized code with detailed explanations
4. Trade-off analysis
5. Implementation recommendations

Code:
{req.code}"""

        reply = await call_gemini_with_retry(
            messages=[
                {"role": "system", "content": SYSTEM_OPTIMIZE},
                {"role": "user", "content": user_msg},
            ]
        )
        return {"reply": reply, "optimization_target": req.objective}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/testbench")
async def generate_testbench(req: TestbenchRequest):
    try:
        # Extract DUT information
        analyzer = VerilogAnalyzer()
        modules = analyzer.extract_modules(req.dut_code)
        
        if not modules:
            raise HTTPException(status_code=400, detail="No modules found in DUT code")
        
        dut_info = f"DUT modules: {[m['name'] for m in modules]}"
        
        user_msg = f"""Generate a comprehensive {req.language} testbench.

DUT Analysis:
{dut_info}

Requirements:
- Test type: {req.test_type}
- Include coverage: {req.include_coverage}
- Language: {req.language}

Generate:
1. Testbench architecture with proper interfaces
2. Clock and reset generation
3. Stimulus generation (directed + random)
4. Self-checking mechanisms
5. Coverage collection
6. Performance metrics
7. Test report generation

DUT Code:
{req.dut_code}"""

        reply = await call_gemini_with_retry(
            messages=[
                {"role": "system", "content": SYSTEM_TESTBENCH},
                {"role": "user", "content": user_msg},
            ]
        )
        return {"reply": reply, "dut_modules": [m['name'] for m in modules]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
async def analyze_code(req: CodeRequest):
    """Comprehensive code analysis without modification"""
    try:
        analyzer = VerilogAnalyzer()
        modules = analyzer.extract_modules(req.code)
        clocks = analyzer.analyze_clock_domains(req.code)
        style_issues = analyzer.check_coding_style(req.code)
        
        # Count lines of code
        loc = len([line for line in req.code.split('\n') if line.strip()])
        
        analysis_summary = {
            "modules": len(modules),
            "clock_domains": len(clocks),
            "lines_of_code": loc,
            "style_issues": len(style_issues)
        }
        
        user_msg = f"""Provide a comprehensive analysis of this Verilog code:

Metrics:
- Modules: {len(modules)}
- Clock domains: {len(clocks)}
- Lines of code: {loc}
- Style issues: {len(style_issues)}

Analysis areas:
1. Design complexity and maintainability
2. Synthesis implications and resource usage
3. Timing considerations
4. Power implications  
5. Verification challenges
6. Industry best practices compliance
7. Portability across tools/vendors

Code:
{req.code}"""

        reply = await call_gemini_with_retry(
            messages=[
                {"role": "system", "content": SYSTEM_BASE + "\nProvide detailed technical analysis without modifying the code."},
                {"role": "user", "content": user_msg},
            ]
        )
        
        return {
            "reply": reply,
            "metrics": analysis_summary,
            "details": {
                "modules": modules,
                "clock_domains": clocks,
                "style_issues": style_issues
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/explain")
async def explain(req: CodeRequest):
    try:
        # Enhanced analysis for better explanations
        analyzer = VerilogAnalyzer()
        modules = analyzer.extract_modules(req.code)
        clocks = analyzer.analyze_clock_domains(req.code)
        
        context = f"""
Code context:
- Modules: {[m['name'] for m in modules]}
- Clock domains: {clocks}
- Complexity: {'High' if len(req.code.split('\n')) > 100 else 'Medium' if len(req.code.split('\n')) > 50 else 'Low'}
"""
        
        user_msg = f"""Explain this Verilog code for a {req.analysis_depth} level understanding.

{context}

Structure your explanation:
1. Overview and purpose
2. Module interface (ports and parameters)
3. Internal architecture
4. Key design decisions
5. Timing and clocking
6. Reset methodology
7. Potential applications
8. Learning points for students

Code:
{req.code}"""

        reply = await call_gemini_with_retry(
            messages=[
                {"role": "system", "content": SYSTEM_BASE + "\nProvide clear, educational explanations suitable for learning."},
                {"role": "user", "content": user_msg},
            ]
        )
        return {"reply": reply, "context": {"modules": len(modules), "complexity": "analyzed"}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========= File Upload Support =========
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        if not file.filename.endswith(('.v', '.sv', '.vh', '.svh')):
            raise HTTPException(status_code=400, detail="Only Verilog files (.v, .sv, .vh, .svh) are supported")
        
        content = await file.read()
        code = content.decode('utf-8')
        
        # Basic analysis of uploaded file
        analyzer = VerilogAnalyzer()
        modules = analyzer.extract_modules(code)
        
        return {
            "filename": file.filename,
            "size": len(content),
            "modules": [m['name'] for m in modules],
            "preview": code[:500] + "..." if len(code) > 500 else code
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)