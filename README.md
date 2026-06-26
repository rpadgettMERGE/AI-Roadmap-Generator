# MERGE AI Roadmap Generator & Operational Transformation Canvas

An internal AI-powered tool built to translate complex tabular roadmap data (CSV/Google Sheets) into an interactive, beautifully rendered Operational Transformation Canvas. 

## 🏗️ Architecture

This application is designed for rapid iteration and secure cloud deployment:

* **Frontend Framework:** Built on **Streamlit** for a fast, Python-native user interface.
* **AI Processing Engine:** Uses a heavily optimized Prompt Engineering pipeline (via GCP Vertex AI / LLMs) to ingest raw roadmap data, perform strict parent/child hierarchy mapping, calculate pro-rated financials/workloads, and output a strict JSON schema.
* **Visual Renderer:** The Streamlit backend injects the generated JSON into a highly customized, interactive HTML/TailwindCSS template that adheres strictly to MERGE brand guidelines.
* **Hosting & Infrastructure:** Deployed as a serverless container on **Google Cloud Run**, ensuring it scales automatically and incurs zero cost when not in use.
* **Security:** Protected by Google Cloud IAM, restricting access exclusively to authorized MERGE personnel via Google Workspace groups.

---

## 💻 Local Development & Testing

When making changes to the UI, prompt, or data processing logic, you should run the application locally first. Streamlit supports "hot-reloading," meaning you do not need to restart the server every time you save a code change!

### 1. Prerequisites
Ensure you have Python installed and your virtual environment activated.
```bash
pip install -r requirements.txt
```

### 2. Run the App Locally
Use the following command to spin up the local Streamlit server. The included flags disable CORS and XSRF protection, which prevents network proxy issues and allows the app to render smoothly in local iframes.

```bash
python -m streamlit run app.py --server.enableCORS=false --server.enableXsrfProtection=false
```

### 3. Iterating on Code
1. Keep the terminal running.
2. Make your code changes in your IDE and save the file.
3. Look at your browser—Streamlit will prompt you in the top right corner. Click **"Always rerun"** to automatically refresh the app whenever you hit save.

---

## ☁️ Cloud Run Deployment (Live Site)

Once your local testing is complete, you can deploy the app directly to Google Cloud Run. 

### Prerequisites
Make sure you have the [Google Cloud CLI (`gcloud`) installed]([https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)) and are authenticated to the correct MERGE GCP project:
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 1. Deploying / Updating the Live Site
To deploy the application (or **update an existing deployment** with new code), run the following command from the root of your repository. Cloud Run will automatically containerize your source code and deploy it.

```bash
gcloud run deploy ai-roadmap-generator \
  --source . \
  --region us-central1 \
  --memory 1Gi \
  --cpu 1
```
*Note: If prompted to allow unauthenticated invocations, select **No**. We manage access via IAM in the next step.*

### 2. Managing Access (IAM)
The application is securely locked down. Only users in the designated Google Group can access the URL. To enforce or update this policy, run:

```bash
gcloud run services add-iam-policy-binding ai-roadmap-generator \
  --region=us-central1 \
  --member="group:gcp-ai-roadmap-generator-access@mergeworld.com" \
  --role="roles/run.invoker"
```

### 🔄 How to Push an Update
Updating the live application is incredibly simple. 
1. Commit and push your changes to GitHub.
2. Run the `gcloud run deploy ...` command exactly as shown in Step 1. 
3. Cloud Run will build a new revision and seamlessly shift 100% of the traffic to your new code with zero downtime. (You do *not* need to re-run the IAM binding command for updates; permissions persist across revisions).
