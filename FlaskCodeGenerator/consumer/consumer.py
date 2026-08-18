import json
import os
import redis
from litellm import completion
from google.cloud import storage, pubsub_v1
import random


LOCAL_LLAMA_BASE_URL = "http://host.docker.internal:<your_port_number>"
LOCAL_LLAMA_MOCK_KEY = "none"
LOCAL_LLAMA_MODEL_SIG = "openai/mycustommodel"

# Define the dynamic port range boundaries
PORT_RANGE_LOWER = 7100
PORT_RANGE_UPPER = 7900

def upload_to_floci_gcs(bucket_name, destination_blob, content):
    """Streams variable file strings directly into your simulated Floci Cloud Storage bucket."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        if not bucket.exists():
            storage_client.create_bucket(bucket_name)
        blob = bucket.blob(destination_blob)
        blob.upload_from_string(content, content_type="text/plain")
        print(f"[FLOCI GCS] Asset committed successfully: gs://{bucket_name}/{destination_blob}")
    except Exception as e:
        print(f"[FLOCI GCS ERROR] Object storage pipeline write failed: {e}")

def run_dual_stage_ai(r, request_id, notes):
    bucket_name = "local-floci-cloud-bucket"
    target_path = f"app_{request_id}"
    
    try:
        # --- STAGE 1: Architectural Mapping Planning Call ---
        r.hset(f"req:{request_id}", "status", "ANALYZING")
        print(f"\n[CONSUMER] ---> Phase 1 Architecture Blueprint running via Local Server for [{request_id}]")
        
        analysis_response = completion(
            model=LOCAL_LLAMA_MODEL_SIG,
            api_base=LOCAL_LLAMA_BASE_URL,
            api_key=LOCAL_LLAMA_MOCK_KEY,


           messages=[
            {
                "role": "system",
                "content": (
                    "You are an assistant that is supplied with meeting notes with stakeholder describing the wbesite or product user interface. Generate a english technical description in 2 parts frontend and backend. In front end description describe each webpage and after completion of each web define linkage of web page with other web page. In backedn description describe technical details on how to link backend with all the web pages for site creation.Generate output in the format Front end description separted by # and then generate back end description. In both description dont include any names of stakeholders  or any personal details"
                 
                ),
            },
            {
                "role": "user",
                "content": f"Meeting notes:\n{notes}\n\n  ",
            },
        ],
        max_tokens=80000, 
        temperature=0

        )

       
           

        user_ui_description = analysis_response.choices[0].message.content
        
        # --- STAGE 2: Structured Tool Multi-File Source Code Generation ---
        r.hset(f"req:{request_id}", "status", "GENERATING")
        print(f"[CONSUMER] ---> Phase 2 Dynamic Multi-File Code Generation running for [{request_id}]")
        
        SYSTEM_PROMPT = (
        "You are an expert front-end and Flask developer. Your task is to generate "
        "a complete web application based on the user's description. The backend "
        "routes can return mock data (non-functional backend), but the UI must be "
        "fully interactive via client-side elements.\n\n"
        "CRITICAL IMPORT RULES:\n"
        "- The 'app_py' property must contain strictly valid Python 3 code.\n"
        "- DO NOT import non-existent modules like 'flask_core' or 'flask.ext'. Only import from standard libraries, 'flask', or 'werkzeug'.\n"
        "- DO NOT include markdown text block formats like ```python or ``` anywhere inside the property values.\n"
        "- DO NOT start the file with JavaScript-style single line comments like '// app.py'.\n\n"
        "CRITICAL BOOTSTRAP UI INJECTIONS:\n"
        "- CDN integration: Include the Bootstrap 5.3 CSS link tag in the <head> of the document.\n"
        "- Layout: Use a responsive structural layout with a fixed left sidebar (`.col-md-3`) and content workspace (`.col-md-9`).\n"
        "- Dashboard Items: Inject visual metric cards using `.card`, `.card-body`, `.text-white`, and background utilities.\n"
        "- Interactivity: Clicking components must dynamically toggle visibility states using JavaScript event listeners."
         )
    
    

    # 3. Map the strict structure schema via LLM tool parameters
        tools = [
            {
            "type": "function",
            "function": {
                "name": "generate_flask_app",
                "description": "Generates Flask python code and corresponding Bootstrap-styled HTML templates.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app_py": {
                            "type": "string",
                            "description": "The complete source code for app.py including routing logic."
                        },
                        "index_html": {
                            "type": "string",
                            "description": "The main index.html template injecting Bootstrap 5 CDN link, component styles, metrics grids, tables, and JavaScript actions."
                        }
                    },
                    "required": ["app_py", "index_html"]
                }
            }
            }
        ]

    
    
  
        response = completion(
            model="gpt-4o",  # Change to your tool-compatible model choice
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_ui_description}
            ],
                    api_base=LOCAL_LLAMA_BASE_URL,
            api_key=LOCAL_LLAMA_MOCK_KEY,
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "generate_flask_app"}}
        )
        tool_calls = response.choices[0].message.tool_calls
        
        if not tool_calls:
            raise ValueError("The AI model did not trigger the 'generate_flask_app' tool function. Try refining your description.")
            
        
        # 4. Unpack response payloads securely
      
        arguments = json.loads(tool_calls[0].function.arguments)
        
        
        flask_backend_code = arguments.get("app_py")
        ui_html_code = arguments.get("index_html")
        
        upload_to_floci_gcs(bucket_name, f"{target_path}/app.py", flask_backend_code)
        
        # 2. index_html is cleanly partitioned and nested inside a custom 'templates' directory path
        upload_to_floci_gcs(bucket_name, f"{target_path}/templates/index.html", ui_html_code)
        
        
      

        # Force baseline operational configuration blueprints to guarantee local downstream runnability
       
        upload_to_floci_gcs(bucket_name, f"{target_path}/requirements.txt", "Flask==3.0.3\n")
            
        
        dockerfile_content = (
                "FROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\n"
                "RUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nEXPOSE 5000\n"
                "ENV FLASK_APP=app.py\nENV FLASK_RUN_HOST=0.0.0.0\nCMD [\"flask\", \"run\", \"--host=0.0.0.0\"]\n"
            )
        upload_to_floci_gcs(bucket_name, f"{target_path}/Dockerfile", dockerfile_content)

        allocated_host_port = random.randint(PORT_RANGE_LOWER, PORT_RANGE_UPPER)
        compose_content = (
                "version: '3.8'\n\nservices:\n"
                "  app:\n"
                "    build: .\n"
                "    ports:\n"
                 f"      - \"{allocated_host_port}:5000\"\n"
                "    environment:\n"
                "      - FLASK_ENV=development\n"
            )
        upload_to_floci_gcs(bucket_name, f"{target_path}/docker-compose.yml", compose_content)
        storage_bucket_path = f"gs://{bucket_name}/{target_path}"
        # Update tracking database markers
        r.hset(f"req:{request_id}", mapping={
            "status": "COMPLETED", 
            "final_code": storage_bucket_path
        })
        
        print(f"[CONSUMER SUCCESS] Project assets packaged cleanly for transaction mapping key: {request_id}")
        print(f"[STORAGE TRACE] Code target location dropped at: {storage_bucket_path}")
        
    except Exception as e:
        print(f"[CONSUMER EXCEPTION CRASH] Multi-file parsing architecture broken: {e}")
        r.hset(f"req:{request_id}", mapping={"status": f"FAILED: {str(e)}", "final_code": "Generation crashed."})

def main():
    redis_host = os.getenv("REDIS_HOST", "localhost")
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "floci-local")
    topic_id = "ui_generation_pipeline"
    subscription_id = "ui_generation_pipeline_sub"

    r = redis.Redis(host=redis_host, port=6379, decode_responses=True)
    subscriber = pubsub_v1.SubscriberClient()
    topic_path = f"projects/{project_id}/topics/{topic_id}"
    subscription_path = subscriber.subscription_path(project_id, subscription_id)

    try:
        subscriber.create_subscription(request={"name": subscription_path, "topic": topic_path})
    except Exception:
        pass

    print("[CONSUMER] Listening for continuous Floci Pub/Sub queue events...")

    def callback(message):
        try:
            payload = json.loads(message.data.decode("utf-8"))
            # Resolves message fields mapping to: id and meeting notes
            run_dual_stage_ai(r, payload["id"], payload["meeting_notes"])
            message.ack()
        except Exception as e:
            print(f"[CALLBACK PROCESSING ERROR] {e}")
            message.nack()

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    with subscriber:
        try:
            streaming_pull_future.result()
        except KeyboardInterrupt:
            streaming_pull_future.cancel()

if __name__ == "__main__":
    main()
