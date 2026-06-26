import streamlit as st
import pandas as pd
import json
import os
import requests
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# ====================================================================
# 1. SCHEMA DEFINITIONS (Updated for Infinite Timelines)
# ====================================================================
class RoadmapItem(BaseModel):
    id: str = Field(description="Unique ID, e.g., M1a, GTM-1")
    name: str = Field(description="Short Initiative Name, max 4 words")
    duration: int = Field(description="Integer length in months. Default to 1 if missing.")
    startSlot: int = Field(description="Integer start month (1, 2, 3+). Calculate from dependency if missing. Do NOT limit to 24.")
    theme: str = Field(description="Must be exactly: standards, automation, measurement, change, team, tech, or ai")
    borderStyle: str = Field(description="Match theme: standards/measurement/ai=border-l-[#00856C], automation/tech=border-l-[#133B34], team/change=border-l-[#636466]")
    desc: str = Field(description="Detailed 1-sentence description")
    minCost: int = Field(description="Minimum cost integer. 0 if blank.")
    maxCost: int = Field(description="Maximum cost integer. 0 if blank.")
    fteHours: int = Field(description="Estimated FTE hours integer. 0 if blank.")
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
# 2. THE SECURE APP UI (Surgical MERGE Brand Protocol)
# ====================================================================
st.set_page_config(page_title="MERGE AI Roadmap Generator", page_icon="📈")

# --- SURGICAL CSS INJECTION ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Epilogue:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,500;1,9..144,300&display=swap');
        
        .stApp { background-color: #EAE8E3 !important; }
        .stMarkdown, .stText, label { font-family: 'Epilogue', sans-serif !important; color: #212721 !important; }
        h1 { font-family: 'Fraunces', serif !important; font-weight: 300 !important; color: #133B34 !important; letter-spacing: -0.02em !important; margin-bottom: 0.25rem !important; }
        h2, h3 { font-family: 'Fraunces', serif !important; font-weight: 300 !important; color: #00856C !important; letter-spacing: -0.02em !important; }
        .stTextInput label p, .stFileUploader label p { color: #133B34 !important; font-weight: 600 !important; font-size: 1rem !important; }
        
        [data-testid="stFileUploadDropzone"] { background-color: #ffffff !important; border: 2px dashed #00856C !important; border-radius: 8px !important; }
        [data-testid="stFileUploadDropzone"] div { color: #636466 !important; font-family: 'Epilogue', sans-serif !important; }
        [data-testid="stFileUploadDropzone"] button { background-color: #133B34 !important; color: #1ED75F !important; border: none !important; border-radius: 4px !important; font-weight: 600 !important; }
        [data-testid="stFileUploadDropzone"] button * { color: inherit !important; }
        [data-testid="stFileUploadDropzone"] button:hover { background-color: #00856C !important; color: #ffffff !important; }
        
        /* Generate Button */
        .stButton > button[kind="primary"] { background-color: #133B34 !important; color: #1ED75F !important; border: none !important; border-radius: 4px !important; font-family: 'Epilogue', sans-serif !important; font-weight: 600 !important; padding: 0.5rem 1.5rem !important; transition: all 0.3s ease; }
        .stButton > button[kind="primary"] * { color: inherit !important; }
        .stButton > button[kind="primary"]:hover { background-color: #00856C !important; color: #ffffff !important; box-shadow: 0 4px 12px rgba(0, 133, 108, 0.3) !important; }
        .stButton > button[kind="primary"]:focus:not(:active) { border-color: transparent !important; box-shadow: none !important; color: #1ED75F !important; }
        
        .stTextInput input { background-color: #ffffff !important; color: #212721 !important; border: 1px solid #00856C !important; font-family: 'Epilogue', sans-serif !important; border-radius: 4px !important; }
        .stTextInput input:focus { border-color: #133B34 !important; box-shadow: 0 0 0 1px #133B34 !important; }
        [data-testid="stDataFrame"] { background-color: #ffffff !important; border-radius: 8px !important; padding: 8px !important; border: 1px solid #EAE8E3 !important; }
        [data-testid="stUploadedFile"] { background-color: #ffffff !important; border: 1px solid #00856C !important; }
        .merge-lockup { font-family: 'Epilogue', sans-serif; font-weight: 600; color: #00856C; font-variant: small-caps; letter-spacing: 0.05em; margin-bottom: -15px; }

        /* ==================================================== */
        /* 1. THE SPINNER OVERRIDE (BOX METHOD) */
        /* ==================================================== */
        div[data-testid="stSpinner"] {
            background-color: #133B34 !important; /* Dark Green Box */
            padding: 1rem 1.5rem !important;
            border-radius: 8px !important;
            border: 1px solid #00856C !important;
            box-shadow: 0 4px 12px rgba(19, 59, 52, 0.15) !important;
        }
        div[data-testid="stSpinner"] * {
            color: #ffffff !important; /* Embracing the white text! */
            font-family: 'Epilogue', sans-serif !important;
        }
        div[data-testid="stSpinner"] p {
            font-weight: 500 !important;
            font-size: 1rem !important;
            margin: 0 !important;
        }
        div[data-testid="stSpinner"] svg circle {
            stroke: #1ED75F !important; /* Electrolight Green Circle */
        }

        /* ==================================================== */
        /* 2. SUCCESS ALERT OVERRIDE */
        /* ==================================================== */
        div[data-testid="stAlert"] {
            background-color: #00856C !important; /* Solid Viridian Green */
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
        }
        div[data-testid="stAlert"] * {
            color: #ffffff !important; 
            font-family: 'Epilogue', sans-serif !important;
            font-weight: 500 !important;
        }
        div[data-testid="stAlert"] svg {
            fill: #ffffff !important; 
        }

        /* ==================================================== */
        /* 3. SOLID DOWNLOAD BUTTON OVERRIDE */
        /* ==================================================== */
        div[data-testid="stDownloadButton"] > button {
            background-color: #133B34 !important; /* Dark Green */
            border: none !important;
            border-radius: 8px !important;
            transition: all 0.3s ease;
            width: 100%;
            padding: 0.75rem !important;
        }
        div[data-testid="stDownloadButton"] > button * {
            color: #1ED75F !important; /* Electrolight Green */
            font-family: 'Epilogue', sans-serif !important;
            font-weight: 600 !important;
        }
        div[data-testid="stDownloadButton"] > button:hover {
            background-color: #00856C !important; /* Viridian */
            box-shadow: 0 4px 12px rgba(0, 133, 108, 0.3) !important;
            border-color: transparent !important;
        }
        div[data-testid="stDownloadButton"] > button:hover * {
            color: #ffffff !important; 
        }
        div[data-testid="stDownloadButton"] > button:focus,
        div[data-testid="stDownloadButton"] > button:active {
            box-shadow: none !important;
            border: none !important;
            color: #1ED75F !important;
            background-color: #133B34 !important;
        }
    </style>
""", unsafe_allow_html=True)

# The MERGE Brand Lockup
st.markdown('<div class="merge-lockup">MERGE • Built Different</div>', unsafe_allow_html=True)
st.title("Operational Transformation Engine")
st.caption("🔒 Secured by MERGE Enterprise IT (IAP)")
st.markdown("Upload client data to generate a context-aware roadmap engine. Built for the intersection of health and wellness, powered by human insight, creativity, and AI.")

uploaded_file = st.file_uploader("Upload client CSV data", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.markdown("**Data preview:**")
    st.dataframe(df, height=250, width='stretch') 
    
    base_file_name = os.path.splitext(uploaded_file.name)[0]
    default_client_name = base_file_name.replace(" - Comprehensive AI Ro", "").replace("_", " ").strip()
    client_name = st.text_input("Confirm or edit client name", value=default_client_name)
    
    if st.button("Generate operational roadmap", type="primary"):
        if not client_name.strip():
            st.error("Please enter a valid client name before generating.")
            st.stop()
            
        with st.spinner("Analyzing human insights, calculating dependencies, and structuring data..."):
            try:
                csv_string = df.to_string()
                client = genai.Client(vertexai=True, project="cop-g-ai-productivity", location="us-central1")
                
                # --- ADVANCED PROMPT: WATERFALL DATES, STRICT HIERARCHY, FINANCIAL RANGES & STRICT MATH ---
                prompt = f"""
                You are an expert Solutions Architect. Analyze this roadmap CSV data and translate it into the required JSON schema.
                The client name is explicitly: {client_name}
                
                CRITICAL PARENT/CHILD MAPPING INSTRUCTIONS:
                1. STRICT FILTERING (CRITICAL): ONLY create a `RoadmapItem` object if the 'Milestones / Tasks' column EXACTLY equals "Initiative". Your final JSON array must ONLY contain Initiatives. NEVER create a standalone roadmap item for a "Sub tasks" row.
                2. SUBTASK GROUPING: Look at the 'ID' column to match "Sub tasks" to their parent "Initiative" (e.g., Subtasks GTM-1.1 and GTM-1.2 belong to the parent Initiative GTM-1).
                3. SUBTASK TEXT: Extract the 'Title' of each grouped Sub task and add it to the parent Initiative's 'subtasks' string array.
                4. DATES & DURATION: For both Initiatives and Sub tasks, read 'Duration (Weeks)' and divide by 4 to get integer months (round up).
                5. START DATE RESOLUTION & WATERFALL DEPENDENCIES: 
                   - Primary Start: Use the 'Start' column as the exact Start Date for the roadmap for each Initiative section.
                   - Dependency Fallback: If an Initiative or Sub task does NOT have a 'Start' date, you MUST look at its dependency (in the 'Dependency' or 'X-Milestone Dependency' columns). 
                   - Chaining Logic: Find the dependency's Start Date and add the dependency's duration to calculate its end date. Set the missing Start Date of the current item to begin immediately at the duration end of its dependency.
                   - BUBBLE UP DEPENDENCIES (For HTML Highlighting): Look at all child "Sub tasks" of an Initiative. If any child Sub task depends on an external Sub task (e.g., GTM-1.1 depends on PS-2.1), you must extract the PARENT Initiative of that blocker (e.g., PS-2) and add it to the current Initiative's `highlightDependencies` array. 
                6. FINANCIALS (RANGES - INITIATIVE ROW ONLY): Read ONLY the row where 'Milestones / Tasks' is "Initiative". Look at 'External vendor cost (low)' (minCost) and 'External vendor cost (high)' (maxCost). Do NOT add, sum, or look at the costs from "Sub tasks" rows. Note that CSV values are in thousands. Strip commas, multiply the value by 1000, and output the exact integer (e.g., 500 -> 500000). If blank, output 0.
                7. WORKLOAD MATH ('fteHours') - CRITICAL ACCURACY & NO SKIPPED ROWS: 
                   - You must process EVERY SINGLE child Sub task for the Initiative. Do not skip any.
                   - In your JSON object, you MUST first populate a string field called `fteCalculationLog`. In this field, write out the math for every subtask like this: "Subtask 1 (4wks * 25% * 40 = 40) + Subtask 2 (12wks * 30% * 40 = 144) ... etc". 
                   - After writing the log, calculate the exact total and output that integer into the `fteHours` field. Treat blank FTE percentages as 0.
                8. THEME: Map the 'Theme ' column of the Initiative to: standards, automation, measurement, change, team, tech, or ai.
                
                Data:
                {csv_string}
                """
                
                response = client.models.generate_content(
                    model='gemini-2.5-pro',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=RoadmapJSON,
                        temperature=0.1, 
                    ),
                )
                
                json_data = json.loads(response.text)
                
                current_est = datetime.now(ZoneInfo("America/New_York"))
                display_date = current_est.strftime("%B %d, %Y") 
                file_safe_date = current_est.strftime("%Y-%m-%d") 
                
                json_data['clientMetadata']['clientName'] = client_name
                json_data['clientMetadata']['assessmentDate'] = display_date
                
                safe_client_name = "".join([c if c.isalnum() else "_" for c in client_name]).strip("_")
                dynamic_filename = f"{safe_client_name}_Operational_Roadmap_{file_safe_date}.html"
                
                json_output = json.dumps(json_data)
                
                with open("base_template.html", "r", encoding="utf-8") as f:
                    base_html = f.read()
                    
                final_html = base_html.replace("__INJECT_JSON_HERE__", json_output)
                
                st.success(f"Successfully generated the roadmap for {client_name}!")
                st.download_button(label=f"⬇️ Download {dynamic_filename}", data=final_html, file_name=dynamic_filename, mime="text/html")
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
