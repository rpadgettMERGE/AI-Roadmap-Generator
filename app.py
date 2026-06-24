import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# ====================================================================
# 1. SCHEMA DEFINITIONS (Forces Gemini to obey your format)
# ====================================================================
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
# 2. THE SECURE APP UI (Surgical MERGE Brand Protocol)
# ====================================================================
st.set_page_config(page_title="MERGE AI Roadmap Generator", page_icon="📈")

# --- SURGICAL CSS INJECTION ---
st.markdown("""
    <style>
        /* Import MERGE Brand Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Epilogue:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,500;1,9..144,300&display=swap');
        
        /* 1. Global App Background */
        .stApp {
            background-color: #EAE8E3 !important; /* Warm Gray */
        }
        
        /* 2. Base Typography */
        .stMarkdown, .stText, label {
            font-family: 'Epilogue', sans-serif !important;
            color: #212721 !important; /* MERGE Black */
        }
        
        /* 3. Headlines */
        h1 {
            font-family: 'Fraunces', serif !important;
            font-weight: 300 !important;
            color: #133B34 !important; /* Dark Green */
            letter-spacing: -0.02em !important;
            margin-bottom: 0.25rem !important;
        }
        
        h2, h3 {
            font-family: 'Fraunces', serif !important;
            font-weight: 300 !important;
            color: #00856C !important; /* Viridian Green */
            letter-spacing: -0.02em !important;
        }

        /* Bold field labels */
        .stTextInput label p, .stFileUploader label p {
            color: #133B34 !important; /* Dark Green */
            font-weight: 600 !important;
            font-size: 1rem !important;
        }

        /* 4. THE UPLOADER DROPZONE */
        [data-testid="stFileUploadDropzone"] {
            background-color: #ffffff !important; /* Force Solid White */
            border: 2px dashed #00856C !important; /* Viridian */
            border-radius: 8px !important;
        }
        
        [data-testid="stFileUploadDropzone"] div {
            color: #636466 !important; /* Medium Gray */
            font-family: 'Epilogue', sans-serif !important;
        }
        
        [data-testid="stFileUploadDropzone"] button {
            background-color: #133B34 !important; /* Dark Green */
            color: #1ED75F !important; /* Electrolight Green */
            border: none !important;
            border-radius: 4px !important;
            font-weight: 600 !important;
        }
        
        [data-testid="stFileUploadDropzone"] button * {
            color: inherit !important; 
        }
        
        [data-testid="stFileUploadDropzone"] button:hover {
            background-color: #00856C !important; /* Viridian */
            color: #ffffff !important;
        }

        /* 5. Primary Action Button ("Generate") */
        .stButton > button[kind="primary"] {
            background-color: #133B34 !important; /* Dark Green */
            color: #1ED75F !important; /* Electrolight Green */
            border: none !important;
            border-radius: 4px !important;
            font-family: 'Epilogue', sans-serif !important;
            font-weight: 600 !important;
            padding: 0.5rem 1.5rem !important;
            transition: all 0.3s ease;
        }
        
        .stButton > button[kind="primary"] * {
            color: inherit !important; 
        }
        
        .stButton > button[kind="primary"]:hover {
            background-color: #00856C !important; /* Viridian Green */
            color: #ffffff !important;
            box-shadow: 0 4px 12px rgba(0, 133, 108, 0.3) !important;
        }
        
        /* 6. Inputs and Dataframes */
        .stTextInput input {
            background-color: #ffffff !important;
            color: #212721 !important; /* Black */
            border: 1px solid #00856C !important; /* Viridian */
            font-family: 'Epilogue', sans-serif !important;
            border-radius: 4px !important;
        }
        
        .stTextInput input:focus {
            border-color: #133B34 !important;
            box-shadow: 0 0 0 1px #133B34 !important;
        }
        
        [data-testid="stDataFrame"] {
            background-color: #ffffff !important;
            border-radius: 8px !important;
            padding: 8px !important;
            border: 1px solid #EAE8E3 !important;
        }
        
        [data-testid="stUploadedFile"] {
            background-color: #ffffff !important;
            border: 1px solid #00856C !important;
        }
        
        /* Small Caps lockup */
        .merge-lockup {
            font-family: 'Epilogue', sans-serif;
            font-weight: 600;
            color: #00856C; /* Viridian */
            font-variant: small-caps; 
            letter-spacing: 0.05em;
            margin-bottom: -15px;
        }
    </style>
""", unsafe_allow_html=True)
# ------------------------------------

# The MERGE Brand Lockup
st.markdown('<div class="merge-lockup">MERGE • Built Different</div>', unsafe_allow_html=True)

# Headline Primary
st.title("Operational Transformation Engine")
st.caption("🔒 Secured by MERGE Enterprise IT (IAP)")

# Body Copy (Human insight, creativity, and AI)
st.markdown("Upload client data to generate a context-aware roadmap engine. Built for the intersection of health and wellness, powered by human insight, creativity, and AI.")

# File Uploader UI
uploaded_file = st.file_uploader("Upload client CSV data", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.markdown("**Data preview:**")
    st.dataframe(df, height=250, width='stretch') 
    
    # Intelligently parse a default client name out of the file name
    base_file_name = os.path.splitext(uploaded_file.name)[0]
    default_client_name = base_file_name.replace(" - Comprehensive AI Ro", "").replace("_", " ").strip()
    
    # Subhead Label
    client_name = st.text_input("Confirm or edit client name", value=default_client_name)
    
    if st.button("Generate operational roadmap", type="primary"):
        if not client_name.strip():
            st.error("Please enter a valid client name before generating.")
            st.stop()
            
        with st.spinner("Analyzing human insights and structuring data..."):
            try:
                # 1. Convert CSV to string for the Agent
                csv_string = df.to_string()
                
                # 2. Call Gemini
                client = genai.Client(
                    vertexai=True, 
                    project="cop-g-ai-productivity", 
                    location="us-central1"
                )
                prompt = f"""
                Analyze this roadmap CSV data and translate it into the required JSON schema.
                The client name is explicitly: {client_name}
                Calculate the 'startSlot' (1-24) based on the dates provided. 
                Assign the correct 'theme' and matching 'borderStyle' hex codes.
                
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
                
                # Parse Gemini's text output into a real Python dictionary
                json_data = json.loads(response.text)
                
                # Get the current EST date
                current_est = datetime.now(ZoneInfo("America/New_York"))
                display_date = current_est.strftime("%B %d, %Y") 
                file_safe_date = current_est.strftime("%Y-%m-%d") 
                
                # Enforce UI changes over the JSON data structure
                json_data['clientMetadata']['clientName'] = client_name
                json_data['clientMetadata']['assessmentDate'] = display_date
                
                # Clean up the name for file output
                safe_client_name = "".join([c if c.isalnum() else "_" for c in client_name]).strip("_")
                dynamic_filename = f"{safe_client_name}_AI_Roadmap_{file_safe_date}.html"
                
                # Turn the dictionary back into a string for the HTML injection
                json_output = json.dumps(json_data)
                
                # Read the base HTML template
                with open("base_template.html", "r", encoding="utf-8") as f:
                    base_html = f.read()
                    
                # Inject the JSON perfectly into the JavaScript
                final_html = base_html.replace("__INJECT_JSON_HERE__", json_output)
                
                st.success(f"Successfully generated the roadmap for {client_name}!")
                
                # Create a Download Button using the dynamic file name
                st.download_button(
                    label=f"⬇️ Download {dynamic_filename}",
                    data=final_html,
                    file_name=dynamic_filename,
                    mime="text/html"
                )
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
