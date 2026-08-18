import json
import time
import os
import uuid
import redis
import random as rd
from litellm import completion
from google.cloud import pubsub_v1

# Slow, safe traffic execution window tailored for local server stability
TRAFFIC_GENERATION_INTERVAL_SECONDS = 180.0 

LOCAL_LLAMA_BASE_URL = "http://host.docker.internal:<your_port_number>"
LOCAL_LLAMA_MOCK_KEY = "none"
LOCAL_LLAMA_MODEL_SIG = "openai/mycustommodelv"

def generate_dynamic_description():
    difficulty_level=rd.choice(["easy","medium","hard"])
    conversation_length=rd.choice(["shory","medium","long"])
 

     
    SYSTEM_PROMPT = f''' You have to generate a meeting notes styled conversation with stakeholder where stakeholder  difficuly level is deifned next. Stakeholder diffculty level is {difficulty_level}.
    Stakeholder will describe the features of the website he wants to get developed.
    Assume if stakeholder is diificult then he/she may not be able to define website clearly where as stakeholder is easy then he/she may be able to deifne wesbite clearly.
    Medium difficulty lies in between.
    Generate a coversation based on the described difficulty level when user asks to generate user will define the conversation length.
    '''
    USER_PROMPT = f'''
    Generate a conversation with length {conversation_length}
    '''


    
    
    try:
        response = completion(
            model=LOCAL_LLAMA_MODEL_SIG,
            api_base=LOCAL_LLAMA_BASE_URL,
            api_key=LOCAL_LLAMA_MOCK_KEY,
            messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":USER_PROMPT}],
                                temperature=0.8,
                    drop_params=True
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[PRODUCER WARNING] LiteLLM generation loop fallback applied: {e}")
        return "Build a standard container fleet allocation manager tracking cluster metrics."

def main():
    redis_host = os.getenv("REDIS_HOST", "localhost")
    r = redis.Redis(host=redis_host, port=6379, decode_responses=True)
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "floci-local")
    topic_id = "ui_generation_pipeline"
    
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_id)
    
    try:
        publisher.create_topic(request={"name": topic_path})
        print(f"[PRODUCER] Topic channel initialized on Floci: '{topic_id}'")
    except Exception:
        pass

    print(f"[PRODUCER RUNNING] Local Llama simulation engine online. Safe slow-rate interval locked at: {TRAFFIC_GENERATION_INTERVAL_SECONDS}s.")

    while True:
        request_id = str(uuid.uuid4())[:8]
        ui_description = generate_dynamic_description()
        
        # Structure your payload packet utilizing your two specified fields: id and mx
        request_payload = {
            "id": request_id,
            "meeting_notes": ui_description
        }
        
        # Keep Redis sync hashes alive for logging tracking milestones
        r.hset(f"req:{request_id}", mapping={
            "id": request_id,
            "initial_parameter": ui_description,
            "status": "QUEUED_IN_PUBSUB",
            "final_code": "Generating..."
        })
        r.lpush("request_list", request_id)
        
        # Publish message directly onto local floci-gcp Pub/Sub hub
        data_bytes = json.dumps(request_payload).encode("utf-8")
        future = publisher.publish(topic_path, data_bytes)
        future.result()
        
        print(f"[SLOW TRAFFIC INJECTION] Sent task signature ID: [{request_id}] -> Waiting {TRAFFIC_GENERATION_INTERVAL_SECONDS}s for local host relaxation...")
        time.sleep(TRAFFIC_GENERATION_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
