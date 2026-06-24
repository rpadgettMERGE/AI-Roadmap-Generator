import os
import pandas as pd
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# ====================================================================
# 1. DEFINE THE STRICT SCHEMA (This forces Gemini to obey your format)
# ====================================================================
class Subtask(BaseModel):
    task: str

class RoadmapItem(BaseModel):
    id: str = Field(description="Unique ID, e.g., M1a, GTM-1")
    name: str = Field(description="Short Initiative Name, max 4 words")
    duration: int = Field(description="Integer length in months")
    startSlot: int = Field(description="Integer start month 1-24")
    theme: str = Field(description="Must be exactly: gtm, tech, team, or ai")
    borderStyle: str = Field(description="gtm=border-l-[#1ED75F], tech=border-l-[#133B34], team=border-l-[#636466], ai=border-l-[#00856C]")
    desc: str = Field(description="Detailed 1-sentence description")
    metrics: str = Field(description="Target metric or ROI")
    deps: list[str] = Field(description="List of IDs this depends on. Empty if none.")
    subtasks: list[str] = Field(description="List of 2-3 short subtask strings")

class RoadmapTrack(BaseModel):
    id: str = Field(description="e.g., track-brand, track-ops")
    focusName: str = Field(description="e.g., Brand & GTM, Marketing Tech")
    trackDesc: str = Field(description="1 sentence summary of the track")
    items: list[RoadmapItem]

class MaturityPhases(BaseModel):
    phase1_text: str = Field(description="Summary of Months 1-6")
    phase2_text: str = Field(description="Summary of Months 7-12")
    phase3_text: str = Field(description="Summary of Months 13-18")
    phase4_text: str = Field(description="Summary of Months 19-24")

class ClientMetadata(BaseModel):
    clientName: str
    assessmentDate: str

class RoadmapJSON(BaseModel):
    clientMetadata: ClientMetadata
    businessMaturityPhases: MaturityPhases
    proportionalRoadmapData: list[RoadmapTrack]

# ====================================================================
# 2. THE AGENT EXECUTION
# ====================================================================
def run_roadmap_agent(csv_filename: str):
    print(f"Reading {csv_filename}...")
    
    # Read the CSV file into a string to feed the agent
    df = pd.read_csv(csv_filename)
    csv_string = df.to_string()

    # Initialize the GenAI Client (Make sure your GCP project is set or API key is exported)
    # Be sure to use your actual GCP project ID and region
    client = genai.Client(
        vertexai=True, 
        project="cop-g-ai-productivity", 
        location="us-central1"
    )

    prompt = f"""
    You are an expert Solutions Architect. Analyze this roadmap CSV data and translate it into the required JSON schema.
    Calculate the 'startSlot' (1-24) based on the dates provided. 
    Assign the correct 'theme' and matching 'borderStyle' hex codes.
    
    Data:
    {csv_string}
    """

    print("Agent is structuring the data. Please wait...")
    
    # The response_schema parameter is the magic bullet here
    response = client.models.generate_content(
        model='gemini-2.5-pro',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RoadmapJSON,
            temperature=0.1, # Keep it highly deterministic
        ),
    )

    # Save the perfect JSON to a file
    output_filename = "final_roadmap_data.json"
    with open(output_filename, "w") as f:
        f.write(response.text)
        
    print(f"Success! JSON saved to {output_filename}")

if __name__ == "__main__":
    # Ensure you export your API key in the terminal first: export GEMINI_API_KEY="your-key"
    run_roadmap_agent("Chartwell - Comprehensive AI Ro.csv")
