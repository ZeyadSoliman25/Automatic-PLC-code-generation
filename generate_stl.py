"""
TIA Portal STL Code Generator
Fills OB1_template.xml with AI-generated CompileUnit networks
via local Qwen3-Coder-Next inference, then writes a ready-to-import XML file.
"""
import torch
import sys
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

# ── Constants ────────────────────────────────────────────────────────────────
MODEL_NAME = "Qwen/Qwen3-Coder-Next"
TEMPLATE_PATH = Path("OB1_template.xml")
OUTPUT_PATH   = Path("OB1_generated.xml")
PLACEHOLDER   = "{{AI_GENERATED_COMPILE_UNITS}}"

SYSTEM_PROMPT = """
You are an expert Siemens TIA Portal STL (Statement List) programmer.
The user describes PLC logic. You must output ONLY the XML CompileUnit blocks
in Siemens TIA Portal Openness V17 format — nothing else.
No explanation, no markdown fences, no extra text.
─── FORMAT RULES ───────────────────────────────────────────────────────────
• Output one <SW.Blocks.CompileUnit> element per network.
• CompositionName must be "CompileUnits" on every unit.
• Each unit gets a unique integer ID starting at 3 (hex for values > 9: A, B, C…).
• StlToken Text values — use EXACTLY these strings:
Instruction │ Text value
────────────┼────────────
A           │  "A "
AN          │  "AN "
O           │  "O "
ON          │  "ON "
A(          │  "A_BRACK "
O(          │  "O_BRACK "
)           │  "BRACKET "
= (assign)  │  "Assign "
S (set)     │  "S "
R (reset)   │  "R "
NOP 0       │  "NOP 0 "
• All I/O variables use Scope="GlobalVariable".
• UId on each StlStatement must be unique integers within the network (start at 24).
• MultilingualText IDs inside each unit must not collide with the unit's own ID.
Use a simple scheme: unit ID × 10 + offset (e.g. unit 3 → text IDs 30, 31, 32, 33).
• Leave network Title and Comment Text nodes empty ( <Text /> ).
─── TEMPLATE FOR ONE NETWORK ────────────────────────────────────────────────
 <SW.Blocks.CompileUnit ID= "3 " CompositionName= "CompileUnits " >
 <AttributeList >
 <NetworkSource > <StatementList xmlns= "http://www.siemens.com/automation/Openness/SW/NetworkSource/StatementList/v4 " >
 <StlStatement UId= "24 " >
 <StlToken Text= "A " / >
 <Access Scope= "GlobalVariable " >
 <Symbol >
 <Component Name= "Input_Variable " / >
 </Symbol >
 </Access >
 </StlStatement >
 <StlStatement UId= "25 " >
 <StlToken Text= "Assign " / >
 <Access Scope= "GlobalVariable " >
 <Symbol >
 <Component Name= "Output_Variable " / >
 </Symbol >
 </Access >
 </StlStatement >
 </StatementList > </NetworkSource >
 <ProgrammingLanguage >STL </ProgrammingLanguage >
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
Output ONLY the raw <SW.Blocks.CompileUnit> block(s).
Start with <SW.Blocks.CompileUnit and end with </SW.Blocks.CompileUnit>.
Multiple networks = multiple elements, one after another, no separator.
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
    """Call local Qwen model and return the raw XML CompileUnit block(s)."""
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

    if "<SW.Blocks.CompileUnit" not in raw:
        raise ValueError(
            "Model response does not contain a CompileUnit block.\n "
            f"Raw response:\n{raw}"
        )

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
def generate_ob1(user_prompt: str,
                 template_path: Path = TEMPLATE_PATH,
                 output_path:   Path = OUTPUT_PATH) -> Path:
    print(f"[1/2] Generating STL networks for prompt:\n      {user_prompt!r}")
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
        prompt = input("Describe the PLC logic to generate:\n> ").strip()

    if not prompt:
        print("No prompt provided. Exiting.")
        sys.exit(1)

    generate_ob1(prompt)