import time
import httpx
import sys
import json

API_URL = "http://localhost:8080/api/v1"

def run_test():
    headers = {
        "Authorization": "Bearer dev-bypass-token"
    }
    
    print("Starting review...")
    start_payload = {
        "repository_id": "64e085e4-1305-4bd7-85a3-80d684351329",
        "files": ["src/core/config.py"]
    }
    
    try:
        start_resp = httpx.post(f"{API_URL}/reviews/start", json=start_payload, headers=headers, timeout=10.0)
        start_resp.raise_for_status()
        start_data = start_resp.json()
        review_id = start_data["review_id"]
        print(f"Started review successfully. Review ID: {review_id}")
    except Exception as e:
        print(f"Failed to start review: {e}")
        if hasattr(e, 'response') and getattr(e, 'response', None) is not None:
            print(e.response.text)
        sys.exit(1)
        
    print("Polling for review status...")
    status = "pending"
    poll_interval = 2
    
    while status in ("pending", "in_progress"):
        time.sleep(poll_interval)
        try:
            get_resp = httpx.get(f"{API_URL}/reviews/{review_id}", headers=headers, timeout=10.0)
            get_resp.raise_for_status()
            get_data = get_resp.json()
            status = get_data["status"]
            print(f"Status: {status}")
        except Exception as e:
            print(f"Error polling status: {e}")
            if hasattr(e, 'response') and getattr(e, 'response', None) is not None:
                print(e.response.text)
            
    print(f"\nFinal status reached: {status}")
    
    try:
        final_resp = httpx.get(f"{API_URL}/reviews/{review_id}", headers=headers, timeout=10.0)
        final_data = final_resp.json()
    except Exception as e:
        print(f"Failed to fetch final review details: {e}")
        sys.exit(1)
        
    print("\n--- FINAL REPORT ---")
    print(f"Review ID: {review_id}")
    print(f"Final Status: {status}")
    
    duration_ms = final_data.get("duration_ms")
    print(f"Total Duration: {duration_ms} ms")
    
    if status == "failed":
        print("\nReview failed. (This may be a quota failure. 429 RESOURCE_EXHAUSTED).")
        print(f"Findings: {final_data.get('findings_json')}")
        print(f"Performance Score: {final_data.get('performance_score')}")
        print(f"Architecture Score: {final_data.get('architecture_score')}")
        return
        
    findings = final_data.get("findings_json", [])
    print(f"\nNumber of findings: {len(findings) if findings else 0}")
    
    if findings:
        for idx, finding in enumerate(findings):
            severity = finding.get("severity", "unknown")
            issue = finding.get("issue", "")
            print(f"  {idx + 1}. [{severity.upper()}] {issue}")
    
    try:
        arch_resp = httpx.get(f"{API_URL}/reviews/{review_id}/architecture", headers=headers, timeout=10.0)
        arch_data = arch_resp.json()
        print("\n--- Architecture & Quality Scores ---")
        print(f"Overall Health Score: {arch_data.get('overall_health_score')}")
        print(f"Complexity Score: {arch_data.get('complexity_score')}")
        print(f"Documentation Score: {arch_data.get('documentation_score')}")
        print(f"Maintainability Score: {arch_data.get('maintainability_score')}")
    except Exception as e:
        print(f"Failed to fetch architecture scores: {e}")

if __name__ == "__main__":
    run_test()
