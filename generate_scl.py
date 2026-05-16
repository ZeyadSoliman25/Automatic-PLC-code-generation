"""
TIA Portal SCL Code Generator
Fills OB1_SCL_template.xml with AI-generated CompileUnit networks
via local Qwen3-Coder-Next inference, then writes a ready-to-import XML file.
Key difference from the STL generator:
SCL networks embed code as a plain-text <ST> block inside <StructuredText>,
not as individual tokenised <StlStatement> elements.
This makes the XML simpler but the SCL code itself must be syntactically
valid Structured Control Language (IEC 61131-3 / Siemens dialect).
"""
import torch
import sys
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

# ── Constants ────────────────────────────────────────────────────────────────
MODEL_NAME = "Qwen/Qwen3-Coder-Next"
TEMPLATE_PATH = Path("OB1_SCL_template.xml")
OUTPUT_PATH   = Path("OB1_SCL_generated.xml")
PLACEHOLDER   = "{{AI_GENERATED_COMPILE_UNITS}}"

SYSTEM_PROMPT = """
You are an expert Siemens TIA Portal SCL (Structured Control Language) programmer.
The user describes PLC logic. You must output ONLY the XML CompileUnit blocks
in Siemens TIA Portal Openness V17 SCL format — nothing else.
No explanation, no markdown fences, no extra text whatsoever.
═══════════════════════════════════════════════════════════════════
CRITICAL DIFFERENCES: SCL vs STL in TIA Openness XML
═══════════════════════════════════════════════════════════════════
STL uses:  <StatementList> with individual <StlStatement>/<StlToken> elements
SCL uses:  <StructuredText> with a single <ST> text node containing the SCL source
The SCL source code lives verbatim inside the <ST> element.
It must be valid XML (escape & → &  < → <  > → >).
Do NOT use CDATA sections — write escaped plain text.
═══════════════════════════════════════════════════════════════════
FORMAT RULES
═══════════════════════════════════════════════════════════════════
One <SW.Blocks.CompileUnit> per logical network/section.
CompositionName must be "CompileUnits" on every unit.
Unit IDs: unique integers starting at 3.
For values > 9 use hex: A, B, C, D, E, F, 10, 11 …
MultilingualText IDs inside each unit must not collide with the unit ID.
Scheme: unit_id_decimal × 10 + offset
Example: unit ID="3" → text IDs 30, 31, 32, 33
UId on each StlStatement (if any) must be unique integers within network.
Leave Title and Comment <Text /> nodes empty.
ProgrammingLanguage element must be "SCL".
═══════════════════════════════════════════════════════════════════
SCL LANGUAGE RULES (Siemens dialect, TIA Portal V17)
═══════════════════════════════════════════════════════════════════
• Global variable references:  "VariableName"  (double-quoted)
• Assignments:                  "Output" := expression;
• IF / ELSIF / ELSE / END_IF
• FOR / TO / BY / DO / END_FOR
• WHILE / DO / END_WHILE
• CASE / OF / ELSE / END_CASE
• Function calls:               FC_Name(param := value);
• FB instance calls:            #instance.method  or  instance(params);
• Boolean literals:             TRUE  FALSE
• Comparison operators:         =  <>  <  >  <=  >=
• Logical operators:            AND  OR  NOT  XOR
• Arithmetic:                   +  -  *  /  MOD
• Comments:                     // single line    (* multi line *)
• Statements end with semicolons.
• String literals use single quotes: 'text'
• Do NOT use Pascal-style BEGIN…END blocks.
═══════════════════════════════════════════════════════════════════
TEMPLATE FOR ONE NETWORK
═══════════════════════════════════════════════════════════════════
<SW.Blocks.CompileUnit ID= "3 " CompositionName= "CompileUnits " >
 <AttributeList >
 <NetworkSource > <StructuredText xmlns= "http://www.siemens.com/automation/Openness/SW/NetworkSource/StructuredText/v4 " >
 <ST > "Motor_relay " := ( "Start " OR  "Motor_relay ") AND NOT  "Stop "; </ST >
 </StructuredText > </NetworkSource >
 <ProgrammingLanguage >SCL </ProgrammingLanguage >
 </AttributeList >
 <ObjectList >
 <MultilingualText ID= "30 " CompositionName= "Comment " >
 <ObjectList >
 <MultilingualTextItem ID= "31 " CompositionName= "Items " >
 <AttributeList >
 <Culture >en-US </Culture >
 <Text / >
 </AttributeList >
 </MultilingualTextItem >
 </ObjectList >
 </MultilingualText >
 <MultilingualText ID= "32 " CompositionName= "Title " >
 <ObjectList >
 <MultilingualTextItem ID= "33 " CompositionName= "Items " >
 <AttributeList >
 <Culture >en-US </Culture >
 <Text / >
 </AttributeList >
 </MultilingualTextItem >
 </ObjectList >
 </MultilingualText >
 </ObjectList >
 </SW.Blocks.CompileUnit >
═══════════════════════════════════════════════════════════════════
MULTI-LINE SCL EXAMPLE (motor + fault logic)
═══════════════════════════════════════════════════════════════════
<SW.Blocks.CompileUnit ID= "3 " CompositionName= "CompileUnits " >
 <AttributeList >
 <NetworkSource > <StructuredText xmlns= "http://www.siemens.com/automation/Openness/SW/NetworkSource/StructuredText/v4 " >
 <ST >// Motor seal-in circuit
 "Motor_relay " := ( "Start " OR  "Motor_relay ") AND NOT  "Stop ";
// Output assignment
 "Motor " :=  "Motor_relay "; </ST >
 </StructuredText > </NetworkSource >
 <ProgrammingLanguage >SCL </ProgrammingLanguage >
 </AttributeList >
 <ObjectList >
 <MultilingualText ID= "30 " CompositionName= "Comment " >
 <ObjectList >
 <MultilingualTextItem ID= "31 " CompositionName= "Items " >
 <AttributeList >
 <Culture >en-US </Culture >
 <Text / >
 </AttributeList >
 </MultilingualTextItem >
 </ObjectList >
 </MultilingualText >
 <MultilingualText ID= "32 " CompositionName= "Title " >
 <ObjectList >
 <MultilingualTextItem ID= "33 " CompositionName= "Items " >
 <AttributeList >
 <Culture >en-US </Culture >
 <Text / >
 </AttributeList >
 </MultilingualTextItem >
 </ObjectList >
 </MultilingualText >
 </ObjectList >
 </SW.Blocks.CompileUnit >
═══════════════════════════════════════════════════════════════════
OUTPUT RULES
═══════════════════════════════════════════════════════════════════
• Start your output with  <SW.Blocks.CompileUnit
• End   your output with  </SW.Blocks.CompileUnit >
• Multiple networks = multiple elements, one after another, no separator.
• XML-escape special characters inside  <ST >:
 &  →   &
 <  →   <
 >  →   >
 "  →   "   (only inside XML attributes, not inside  <ST > text)
Note: Siemens double-quoted variable names  "VarName " inside  <ST >
do NOT need escaping because they are text content, not XML attributes.
"""

# ── Model Initialization (4-bit Quantization) ───────────────────────────────
print("Loading Qwen3-Coder-Next with 4-bit NF4 quantization...")
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,
    device_map="auto",
    torch_dtype=torch.float16,
)
model.eval()

# ── AI call ──────────────────────────────────────────────────────────────────
def generate_compile_units(user_prompt: str) -> str:
    """Call local Qwen model and return the raw XML CompileUnit block(s) in SCL format."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=4096,
            temperature=0.1,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    raw = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True).strip()

    # SCL-specific validation
    if "<SW.Blocks.CompileUnit" not in raw:
        raise ValueError("Model response does not contain a CompileUnit block.")
    if "<StructuredText" not in raw:
        raise ValueError("Model response does not contain a StructuredText block — generated wrong language.")
    if "<ST>" not in raw:
        raise ValueError("Model response is missing the <ST> element that carries SCL source.")

    return raw

# ── Template injection ────────────────────────────────────────────────────────
def inject_into_template(compile_units_xml: str,
                         template_path: Path = TEMPLATE_PATH,
                         output_path:   Path = OUTPUT_PATH) -> Path:
    template = template_path.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise ValueError(f"Placeholder '{PLACEHOLDER}' not found in template '{template_path}'.")

    filled = template.replace(PLACEHOLDER, compile_units_xml)
    output_path.write_text(filled, encoding="utf-8")
    return output_path

# ── Public entry point ────────────────────────────────────────────────────────
def generate_ob1_scl(user_prompt: str,
                     template_path: Path = TEMPLATE_PATH,
                     output_path:   Path = OUTPUT_PATH) -> Path:
    print(f"[1/2] Generating SCL networks for prompt:\n      {user_prompt!r}")
    compile_units = generate_compile_units(user_prompt)
    network_count = compile_units.count("<SW.Blocks.CompileUnit")
    print(f"      → {network_count} network(s) generated")

    print(f"[2/2] Injecting into template → {output_path}")
    result = inject_into_template(compile_units, template_path, output_path)
    print(f"      Done. File ready for TIA Portal import: {result.resolve()}")
    return result

# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = input("Describe the PLC logic to generate (SCL):\n> ").strip()

    if not prompt:
        print("No prompt provided. Exiting.")
        sys.exit(1)

    generate_ob1_scl(prompt)