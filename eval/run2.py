import asyncio
import json
import time
import sys
import os
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.agent.redact import redact
from backend.agent.extract import extract_event

async def run_evals():
    dataset_path = os.path.join(os.path.dirname(__file__), "dataset_hard.jsonl")
    
    print("🚀 Starting NudgeBox STRICT LLM Evaluation (Spam & Noise Test)...\n")
    
    total_emails = 0
    correct_is_event = 0
    correct_kind = 0
    false_positives = 0
    false_negatives = 0
    latencies = []
    
    with open(dataset_path, "r") as f:
        for line in f:
            if not line.strip(): continue
            
            data = json.loads(line)
            email_text = data["text"]
            total_emails += 1
            
            print(f"📧 Processing Email #{data['id']} (True Event: {data['label_is_event']})...")
            redacted_text = redact(email_text)
            
            start_time = time.time()
            try:
                event = await extract_event(redacted_text, "Thu, 15 Oct 2026 10:00:00 +0000")
                latency = time.time() - start_time
                latencies.append(latency)
                
                # Check metrics
                if event.is_event == data["label_is_event"]:
                    correct_is_event += 1
                    print(f"  ✅ PASS: correctly identified as {event.is_event}")
                else:
                    print(f"  ❌ FAIL: Expected {data['label_is_event']}, got {event.is_event}")
                    if event.is_event:
                        false_positives += 1
                        print("  🚨 FALSE POSITIVE: Model got tricked by spam/clickbait!")
                    else:
                        false_negatives += 1
                        print("  🚨 FALSE NEGATIVE: Model missed a real interview!")
                        
                if event.is_event and event.kind == data["label_kind"]:
                    correct_kind += 1
                    
            except Exception as e:
                print(f"  ❌ API Error: {e}")
                
    print("\n" + "="*60)
    print("📊 STRICT EVALUATION RESULTS")
    print("="*60)
    print(f"Total Emails Processed: {total_emails}")
    print(f"Overall Accuracy: {(correct_is_event/total_emails)*100:.1f}%")
    print(f"False Positives (Tricked by Spam): {false_positives}")
    print(f"False Negatives (Missed Interviews): {false_negatives}")
    
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        print(f"Average Latency per email: {avg_latency:.2f} seconds")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_evals())
