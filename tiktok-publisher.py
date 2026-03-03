import os
import argparse
import time
import requests
import json
from pathlib import Path

# ==========================================
# TikTok Auto-Publisher CLI (Python)
# ==========================================

def get_auth_url(client_key):
    """Generate the OAuth authorization URL for the user to visit"""
    redirect_uri = "https://www.tiktok.com/" # Simple dummy redirect for standalone
    url = f"https://www.tiktok.com/v2/auth/authorize/?client_key={client_key}&response_type=code&scope=video.upload&redirect_uri={redirect_uri}"
    return url

def get_access_token(client_key, client_secret, code):
    """Exchange the authorization code for an entry access token"""
    url = "https://open.tiktokapis.com/v2/oauth/token/"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "client_key": client_key,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": "https://www.tiktok.com/"
    }
    
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting access token: {response.text}")
        return None

def init_upload(access_token, video_path):
    """Initialize the video upload process with TikTok"""
    file_size = os.path.getsize(video_path)
    
    url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "post_info": {
            "title": "Auto-published from CLI tool #fyp",
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
            "video_cover_timestamp_ms": 1000
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": file_size,
            "chunk_size": file_size, 
            "total_chunk_count": 1
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error initializing upload: {response.text}")
        return None

def upload_video(upload_url, video_path):
    """Upload the actual video byte stream to the provided URL"""
    file_size = os.path.getsize(video_path)
    headers = {
        "Content-Range": f"bytes 0-{file_size-1}/{file_size}",
        "Content-Type": "video/mp4"
    }
    
    with open(video_path, 'rb') as f:
        video_data = f.read()
        
    print(f"Uploading file chunks... ({file_size} bytes)")
    response = requests.put(upload_url, headers=headers, data=video_data)
    
    if response.status_code in [200, 201]:
        print("Video chunk upload complete!")
        return True
    else:
        print(f"Error uploading video chunk: {response.text}")
        return False

def check_status(access_token, publish_id):
    """Poll the status of the published video"""
    url = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {"publish_id": publish_id}
    
    print("Waiting for TikTok to process the video...")
    for _ in range(10): # Try config 10 times
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            status = response.json().get('data', {}).get('status')
            if status == "PUBLISH_COMPLETE":
                print("✅ Video successfully published to TikTok!")
                return True
            elif status == "FAILED":
                print("❌ TikTok failed to publish the video.")
                return False
        time.sleep(5)
    
    print("Timed out waiting for confirmation, but it might still be processing.")
    return False

def main():
    parser = argparse.ArgumentParser(description="TikTok Auto-Publisher CLI Tool")
    parser.add_argument("video", help="Path to the video file to upload (.mp4, .webm)")
    parser.add_argument("--count", type=int, default=1, help="Number of times to post the video (Spam amount)")
    args = parser.parse_args()
    
    if not os.path.exists(args.video):
        print(f"Error: Video file not found at '{args.video}'")
        return
        
    print("\n" + "="*50)
    print("🔥 TikTok Auto-Publisher v1.0 🔥")
    print("="*50 + "\n")
    
    # 1. Provide Config
    client_key = input("Enter your TikTok App Client Key: ")
    client_secret = input("Enter your TikTok App Client Secret: ")
    
    if not client_key or not client_secret:
        print("Please provide valid TikTok Application Credentials.")
        return
        
    # 2. Get User Authorization
    auth_url = get_auth_url(client_key)
    print("\n[STEP 1] Please open the following URL in your browser to authorize this tool:")
    print(f"\n---> {auth_url} <---")
    print("\nAfter clicking Authorize, you will be redirected to a URL that looks breaking.")
    print("Look at the URL address bar and copy the text after 'code='")
    
    auth_code = input("\nEnter the Authorization Code: ")
    
    # 3. Exchange Code for Access Token
    print("\n[STEP 2] Fetching Access Token...")
    token_data = get_access_token(client_key, client_secret, auth_code)
    
    if not token_data or "access_token" not in token_data:
        print("Failed to get Access Token. The authorization code might have expired.")
        return
        
    access_token = token_data["access_token"]
    print(f"Successfully connected to TikTok API!")
    
    # 4. Spammer Publish Loop
    print(f"\n[STEP 3] Preparing to publish '{args.video}' {args.count} times...")
    
    for i in range(args.count):
        print(f"\n--- Publishing Iteration {i+1} of {args.count} ---")
        
        # Init Post
        init_data = init_upload(access_token, args.video)
        if not init_data or "data" not in init_data:
            continue
            
        publish_id = init_data["data"]["publish_id"]
        upload_url = init_data["data"]["upload_url"]
        
        # Upload Bytes
        success = upload_video(upload_url, args.video)
        if success:
            # Check Status
            check_status(access_token, publish_id)
            
        if i < args.count - 1:
            print(f"Waiting 10 seconds before next post to avoid immediate API rate limits...")
            time.sleep(10)
            
    print("\n🎉 Auto-Publishing Complete! 🎉")

if __name__ == "__main__":
    main()
