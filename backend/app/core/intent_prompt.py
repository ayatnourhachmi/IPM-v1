# Intent prompt builder for LLM calls

def build_intent_prompt(explicit: str, implicit: str, strategic: str, context: str) -> str:
    """
    Build a prompt with explicit, implicit, and strategic intent layers, plus context.
    Strategic intent must always include: "position DXC as trusted delivery partner".
    """
    # Ensure strategic intent always includes the required phrase
    required_phrase = "position DXC as trusted delivery partner"
    if required_phrase.lower() not in strategic.lower():
        strategic = f"{strategic.strip()}\n{required_phrase}"
    return f"""
[EXPLICIT INTENT]
{explicit}

[IMPLICIT INTENT]
{implicit}

[STRATEGIC INTENT - DXC POSITIONING]
{strategic}

[CONTEXT]
{context}
"""
