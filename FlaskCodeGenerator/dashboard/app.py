import io
import os
import zipfile
import redis
from flask import Flask, render_template_string, send_file, abort
from google.cloud import storage

app = Flask(__name__)

# Connect to the centralized Redis instance running in the cluster
redis_host = os.getenv("REDIS_HOST", "localhost")
r = redis.Redis(host=redis_host, port=6379, decode_responses=True)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Pipeline Trace Monitor</title>
    <!-- Modern Bootstrap CSS for clean typography and spacing -->
    <link href="https://jsdelivr.net" rel="stylesheet">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        th { background-color: #f8f9fa !important; font-size: 0.85rem; letter-spacing: 0.5px; text-transform: uppercase; font-weight: 600; color: #495057; }
        .table-responsive { border-radius: 8px; border: 1px solid #e9ecef; }
        .font-monospace-custom { font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 0.9rem; }
    </style>
</head>
<body class="bg-light">
    <div class="container-fluid px-4 my-4">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <div>
                <h4 class="mb-0 text-dark fw-bold">Pipeline Operations Workspace</h4>
                <p class="text-muted small mb-0">Decoupled Local Machine Llama Server Generation Logs</p>
            </div>
            <a href="/" class="btn btn-sm btn-outline-primary shadow-sm px-3">Refresh Data Table</a>
        </div>
        
        <div class="card shadow-sm border-0 rounded-3">
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                    <thead>
                        <tr>
                            <th style="width: 20%;" class="ps-3 py-3">Request ID</th>
                              <th style="width: 15%;" class="py-3">Status</th>
                            <th style="width: 33%;" class="py-3">UI Specification Plan</th> 
                            <th style="width: 50%;" class="py-3">Storage Bucket Location (final_code)</th>
                            <th style="width: 15%; text-align: center;" class="pe-3 py-3">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in items %}
                        <tr>
                            <td class="ps-3"><strong class="text-primary font-monospace-custom">{{ item.id }}</strong></td>
                            <td>
                                <span class="badge {% if item.status=='COMPLETED' %}bg-success{% elif 'FAILED' in item.status %}bg-danger{% else %}bg-warning text-dark{% endif %} px-2.5 py-1.5 rounded">
                                    {{ item.status }}
                                </span>
                            </td>
                               <td>
                                <div class="text-dark small" style="line-height: 1.5; max-height: 80px; overflow-y: auto; padding-right: 5px;">
                                    {{ item.initial_parameter }}
                                </div>
                                </span>
                            </td>
                            <td>
                                <span class="font-monospace-custom text-secondary small bg-white border px-2 py-1 rounded d-inline-block border-opacity-75">
                                    {{ item.final_code }}
                                </span>
                            </td>
                            <td class="text-center pe-3">
                                {% if item.status == 'COMPLETED' %}
                                <a href="/download/{{ item.id }}" class="btn btn-sm btn-primary shadow-sm py-1 px-3 fw-medium" style="font-size: 0.85rem;">Download Bundle</a>
                                {% else %}
                                <button class="btn btn-sm btn-secondary py-1 px-3" style="font-size: 0.85rem;" disabled>In Progress</button>
                                {% endif %}
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="4" class="text-center text-muted py-5 small">No tracking transactions found. Run the orchestration containers to stream traffic tasks from your local Llama server.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    request_ids = r.lrange("request_list", 0, -1)
    items = []
    for req_id in request_ids:
        data = r.hgetall(f"req:{req_id}")
        if data:
            raw_param = data.get("initial_parameter", "")
            
            # --- THE NEW SANITIZATION LAYER ---
            sanitized_param = raw_param.replace("```text", "").replace("```", "")
            sanitized_param = sanitized_param.strip().strip('"').strip("'").strip()
            
            data["initial_parameter"] = sanitized_param
            items.append(data)
    return render_template_string(HTML_TEMPLATE, items=items)


@app.route("/download/<request_id>")
def download_bundle(request_id):
    """
    Fetches generated source assets straight out of the local Floci GCS bucket memory space.
    Compresses them on the fly into a clean ZIP archive with nested paths intact.
    """
    status = r.hget(f"req:{request_id}", "status")
    if status != "COMPLETED":
        abort(400, description="The compilation workflow for this request path context is incomplete.")

    bucket_name = "local-floci-cloud-bucket"
    prefix = f"app_{request_id}/"
    
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix=prefix))
        
        if not blobs:
            abort(404, description="No runtime code deployment assets found inside the Floci storage prefix path.")
            
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for blob in blobs:
                # Strip off the root bucket subfolder wrapper to isolate the code package internally
                relative_file_path = blob.name.replace(prefix, "")
                file_bytes = blob.download_as_bytes()
                zf.writestr(relative_file_path, file_bytes)
                
        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"bootstrap_app_{request_id}.zip"
        )
    except Exception as e:
        abort(500, description=f"Internal aggregation package engine failure: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
