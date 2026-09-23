import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.infrastructure.ingestion.pdf_parser import PdfParser
from app.infrastructure.ai.agents.content_understanding_agent import ContentUnderstandingAgent

async def main():
    pdf_path = "test_data/input/Ch 3 Mineral and Power Resour.pdf"
    print(f"Parsing: {pdf_path}")
    parser = PdfParser()
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()
    doc = parser.parse(file_bytes, "test.pdf")
    
    print("Length of raw text:", len(doc.raw_text))
    
    agent = ContentUnderstandingAgent()
    
    # We will temporarily override the base agent's generate_structured to print prompts
    original_generate_structured = agent.generate_structured
    
    async def debug_generate_structured(prompt_name, schema=None, context=None, **kwargs):
        prompt = agent._build_prompt(prompt_name, context)
        print("\n" + "="*50)
        print(f"PROMPT SENT TO LLM ({prompt_name}):")
        print(prompt[:1000])
        print("..." if len(prompt) > 1000 else "")
        print("="*50 + "\n")
        
        # Let's call provider generate to see raw response
        response = await agent.provider.generate(prompt)
        print("\n" + "="*50)
        print("RAW RESPONSE FROM PROVIDER:")
        print(response.content)
        print("="*50 + "\n")
        
        return await original_generate_structured(prompt_name, schema, context, **kwargs)
        
    agent.generate_structured = debug_generate_structured
    
    print("Running ContentUnderstandingAgent...")
    understanding = await agent.run(doc)
    print("Agent output:")
    print(understanding.model_dump_json(indent=2))

if __name__ == "__main__":
    asyncio.run(main())
